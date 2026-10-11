"""Supprime (désenvoie) TES propres messages dans un groupe Instagram configuré localement.

- Ne touche qu'aux messages du compte connecté, jamais à ceux des autres.
- Aucun LLM, aucune clé API : juste ton identifiant Instagram.
- Reprise automatique : si tu arrêtes (Ctrl+C) ou si ça plante, relance, ça repart
  où ça s'était arrêté (fichier etat.json).
- S'arrête tout seul si Instagram demande une vérification ou dit de ralentir.
"""
import getpass, json, os, random, sys, tempfile, time
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import (ChallengeRequired, ClientError, LoginRequired,
                                   PleaseWaitFewMinutes, RateLimitError,
                                   TwoFactorRequired)

DOSSIER = Path(__file__).resolve().parent
CONFIG = DOSSIER / 'config.json'     # configuration locale (ne pas partager)
SESSION = DOSSIER / 'session.json'   # ta session Instagram (ne la partage pas)
ETAT = DOSSIER / 'etat.json'         # progression, pour reprendre
MESSAGES_SYSTEME = {'action_log', 'video_call_event'}  # non désenvoyables


def lire_configuration():
    try:
        config = json.loads(CONFIG.read_text(encoding='utf-8'))
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f'{CONFIG.name} manquant. Copie config.example.json en config.json '
            'et renseigne le groupe Instagram.'
        ) from e
    if not isinstance(config, dict):
        raise ValueError(f'{CONFIG.name} doit contenir un objet JSON.')
    groupe_id = config.get('group_id')
    groupe_nom = config.get('group_name')
    if (not isinstance(groupe_id, str) or not groupe_id.isascii()
            or not groupe_id.isdigit()):
        raise ValueError(f'group_id dans {CONFIG.name} doit être une chaîne numérique.')
    if not isinstance(groupe_nom, str) or not groupe_nom.strip():
        raise ValueError(f'group_name dans {CONFIG.name} ne doit pas être vide.')
    return groupe_id, groupe_nom.strip()


def pause(n):
    """Rythme calme : ~2 s entre deux suppressions, pause plus longue de temps en temps."""
    if n and n % random.randint(25, 40) == 0:
        time.sleep(random.uniform(15, 45))
    else:
        time.sleep(random.lognormvariate(0.7, 0.35))


def lire_etat():
    try:
        return json.loads(ETAT.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def ecrire_etat(d):
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=DOSSIER,
                prefix='etat.', suffix='.tmp', delete=False) as fichier:
            tmp = Path(fichier.name)
            json.dump(d, fichier)
        for tentative in range(5):
            try:
                os.replace(tmp, ETAT)
                break
            except PermissionError as e:
                if tentative == 4:
                    raise PermissionError(
                        f"Impossible de mettre à jour {ETAT.name}. "
                        "Ferme tout programme qui pourrait l'utiliser, "
                        "puis relance le script."
                    ) from e
                time.sleep(0.2 * (tentative + 1))
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass


def connexion():
    c = Client()
    c.delay_range = [1, 3]
    if SESSION.exists():
        c.load_settings(SESSION)
        try:
            c.account_info()
            print(f'✓ Session réutilisée : {c.username}')
            return c
        except LoginRequired:
            print('Session expirée, reconnexion…')
            c = Client(); c.delay_range = [1, 3]
    user = input('Identifiant Instagram : ').strip()
    mdp = getpass.getpass('Mot de passe (invisible quand tu tapes) : ')
    try:
        c.login(user, mdp)
    except TwoFactorRequired:
        code = input('Code de double authentification : ').strip()
        c.login(user, mdp, verification_code=code)
    c.dump_settings(SESSION)
    print(f'✓ Connecté : {c.account_info().username}')
    return c


def page(c, curseur, groupe_id):
    p = {'direction': 'older', 'limit': '20', 'visual_message_return_type': 'unseen'}
    if curseur:
        p['cursor'] = curseur
    return c.private_request(f'direct_v2/threads/{groupe_id}/', params=p)['thread']


def main():
    groupe_id, groupe_nom = lire_configuration()
    c = connexion()
    etat = lire_etat()
    curseur = etat.get('curseur')
    total = etat.get('supprimes', 0)
    pages = etat.get('pages', 0)
    if curseur:
        print(f'Reprise : {total} déjà supprimés, page {pages}.')
    vus = set()
    while True:
        t = page(c, curseur, groupe_id)
        if not t.get('is_group') or t.get('thread_title', '') != groupe_nom:
            sys.exit(f'✗ Le fil trouvé n\'est pas « {groupe_nom} » (ou tu n\'es pas dans ce groupe). Rien supprimé.')
        pages += 1
        mes = [m for m in t.get('items', []) if str(m.get('user_id')) == str(c.user_id)]
        for m in mes:
            if m.get('item_type') in MESSAGES_SYSTEME:
                continue
            try:
                ok = c.direct_message_delete(int(groupe_id), int(m['item_id']))
            except ClientError as e:
                if 'cannot be unsent' in str(getattr(c, 'last_json', {}) or {}):
                    continue
                raise
            if ok:
                total += 1
                print(f'  supprimé #{total} (page {pages})')
            pause(total)
        suivant = t.get('oldest_cursor')
        ecrire_etat({'curseur': curseur, 'supprimes': total, 'pages': pages})
        if t.get('has_older') is False or not suivant or suivant in vus:
            break
        vus.add(suivant)
        curseur = suivant
        ecrire_etat({'curseur': curseur, 'supprimes': total, 'pages': pages})
        time.sleep(random.uniform(0.6, 2.0))
    ecrire_etat({'curseur': None, 'supprimes': total, 'pages': pages, 'fini': True})
    print(f'\n✅ Terminé : {total} messages supprimés, tout l\'historique accessible parcouru.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⏸ Arrêté. Relance plus tard : ça reprendra où ça en était.')
    except (ChallengeRequired, PleaseWaitFewMinutes, RateLimitError) as e:
        print(f'\n⚠️ Instagram demande de ralentir ou une vérification ({type(e).__name__}).')
        print('Ouvre Instagram sur ton téléphone, valide si besoin, attends quelques heures puis relance.')
