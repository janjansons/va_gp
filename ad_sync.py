from ldap3 import Server, Connection, ALL
from datetime import datetime
from models import db, Kartinas, AdGroups, AdSyncLog, UserGroups
from flask import flash

# AD konfigurācija
AD_SERVER = 'ldap://10.9.9.204'  # jj.id.lv
AD_USER = 'JJ\\Administrator'
AD_PASSWORD = 'Airites1243!'
BASE_DN = 'DC=jj,DC=id,DC=lv'


def sync_ad_users_and_groups():
    """
    Sinhronizē lietotājus un grupas no Active Directory uz lokālo datubāzi.
    """
    try:
        # Savienojuma izveide
        server = Server(AD_SERVER, get_info=ALL)
        connection = Connection(server, user=AD_USER, password=AD_PASSWORD)
        connection.open()
        if not connection.bind():
            print('Not Authenticated')
            print(connection.result)
            return

        print("Pieslēgšanās AD veiksmīga!")

        synced_user_dn = []  # Inicializē sarakstu sinhronizētajiem lietotājiem

        # Lietotāju sinhronizācija
        print("Sāk lietotāju sinhronizāciju...")
        connection.search(BASE_DN, '(objectClass=person)',
                          attributes=['givenName', 'sn', 'mail', 'title', 'telephoneNumber', 'sAMAccountName', 'memberOf'])

        # Iegūst visus esošos lietotājus no datubāzes
        existing_users = {u.samaccountname: u for u in Kartinas.query.all()}  # Pārbaude tikai pēc samaccountname
        total_synced = 0
        current_user_samaccountnames = set()

        # Pievienot vai atjaunināt lietotājus
        for entry in connection.entries:
            samaccountname = str(entry.sAMAccountName) if entry.sAMAccountName else None
            if not samaccountname:
                continue  # Izlaist, ja nav pieejams samaccountname

           #epasts = str(entry.mail) if entry.mail else None
            user_dn = entry.entry_dn
            user_groups = entry.memberOf if hasattr(entry, 'memberOf') else []
            
            # Pārbaudīt, vai lietotājs ir grupā "visi_lietotaji"
            is_in_visi_lietotaji = any("CN=visi_lietotaji" in str(group) for group in user_groups)
            if not is_in_visi_lietotaji:
                continue  # Izlaist lietotāju, ja tas nav grupā "visi_lietotaji"

            current_user_samaccountnames.add(samaccountname)

            # Pārbaudīt, vai lietotājs eksistē pēc samaccountname
            user = existing_users.get(samaccountname)

            if user:
                # Atjaunināt esošo lietotāju
                user.vards = str(entry.givenName) if entry.givenName else user.vards
                user.uzvards = str(entry.sn) if entry.sn else user.uzvards
                user.epasts = str(entry.mail) if entry.mail else user.epasts
                user.amats = str(entry.title) if entry.title else user.amats
                user.tel_nr = str(entry.telephoneNumber) if entry.telephoneNumber else user.tel_nr
                user.last_synced = datetime.now()
                print(f"Lietotājs atjaunināts: {samaccountname}")
            else:
                # Pievienot jaunu lietotāju
                new_user = Kartinas(
                    vards=str(entry.givenName) if entry.givenName else None,
                    uzvards=str(entry.sn) if entry.sn else None,
                    epasts=str(entry.mail),
                    tel_nr=str(entry.telephoneNumber) if entry.telephoneNumber else None,
                    amats=str(entry.title) if entry.title else None,
                    samaccountname=samaccountname,
                    acc_date=datetime.now(),
                    last_synced=datetime.now()
                )
                db.session.add(new_user)
                print(f"Jauns lietotājs pievienots: {samaccountname}")

            synced_user_dn.append(user_dn)  # Pievieno lietotāja DN sinhronizēto sarakstam
            total_synced += 1

        db.session.commit()  # Saglabāt izmaiņas datubāzē
        print(f"Kopā sinhronizēti lietotāji: {total_synced}")

        # Grupas sinhronizācija
        print("Sāk grupu sinhronizāciju...")
        connection.search(BASE_DN, '(objectClass=group)', attributes=['cn', 'description', 'member'])

        existing_groups = {g.group_name: g for g in AdGroups.query.all()}

        for group in connection.entries:
            group_name = str(group.cn)
            description = str(group.description) if 'description' in group else ''
            members = group.member if hasattr(group, 'member') else []

            # Pārbaudām, vai grupā ir vismaz viens sinhronizētais lietotājs
            if any(member in synced_user_dn for member in members):
                if group_name not in existing_groups:
                    new_group = AdGroups(group_name=group_name, description=description)
                    db.session.add(new_group)

        db.session.commit()  # Saglabā izmaiņas pēc grupu sinhronizācijas

        # Sasaistīt lietotāja grupas, pamatojoties uz memberOf
        for group_dn in user_groups:
            group_name = group_dn.split(',')[0].split('=')[1]  # Iegūst grupas nosaukumu
            group = AdGroups.query.filter_by(group_name=group_name).first()
            if group:
                # Pārbauda vai nav jau esoša sasaiste
                existing_relation = db.session.query(UserGroups).filter_by(user_id=user.id, group_id=group.group_id).first()
                if not existing_relation:
                    # Ja nav sasaiste
                    user_group_association = UserGroups(user_id=user.id, group_id=group.group_id)
                    db.session.add(user_group_association)  # Pievieno sasaistes ierakstu

        db.session.commit()  # Saglabā izmaiņas pēc lietotāju atjaunināšanas

        # Dzēst lietotājus, kas vairs nav AD
        for samaccountname, user in existing_users.items():
            if samaccountname not in current_user_samaccountnames:
                user.statuss = 3
                # db.session.delete(user)

        db.session.commit()  # Saglabā izmaiņas pēc lietotāju dzēšanas

        print(f"Lietotāji sinhronizēti: {total_synced}")

        # Žurnāla ieraksts
        db.session.add(AdSyncLog(total_users_synced=total_synced))
        db.session.commit()

        flash(f"AD sinhronizācija pabeigta! Kopā sinhronizēti lietotāji: {total_synced}")

    except Exception as e:
        print(f"Kļūda sinhronizācijas laikā: {e}")


if __name__ == '__main__':
    sync_ad_users_and_groups()