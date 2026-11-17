"""Constantes de vmc_stiebel (dérivé de sanderkwantes/mystiebel, Apache 2.0, voir NOTICE.md)."""
from datetime import timedelta

DOMAIN = "vmc_stiebel"

AUTH_URL = "https://auth.mystiebel.com/api/v1/Jwt/login"
INSTALL_URL = "https://serviceapi.mystiebel.com/api/v1/InstallationsInfo/own"
WS_URL = "wss://serviceapi.mystiebel.com/ws/v1"
APP_HEADERS = {
    "X-SC-ClientApp-Name": "MyStiebelApp",
    "X-SC-ClientApp-Version": "Android_2.3.0",
    "User-Agent": "MyStiebelApp/2.3.0 Dalvik/2.1.0",
}

# Seules méthodes JSON-RPC autorisées (pas de Subscribe). setValues n'est envoyé que par
# MyStiebelLecture.ecrire(), limité à REGISTRES_ECRITURE et VALEURS_ECRITURE.
METHODES_AUTORISEES = frozenset({"Login", "getValues", "setValues"})
REGISTRES_ECRITURE = frozenset({2565})  # seul registre modifiable : mode demandé
VALEURS_ECRITURE = range(0, 5)          # 0 à 3 = niveau, 4 = programme horaire
DELAI_ENTRE_ECRITURES = 10              # s, au moins entre deux écritures
RELECTURE_APRES_ECRITURE = 40           # s, relecture pour confirmer (la VMC applique en < 30 s)
JOURNAL_ECRITURES = "vmc_stiebel_writes.log"  # relatif au dossier de configuration de HA

INTERVALLE_REGISTRES = timedelta(minutes=2)
INTERVALLE_INSTALLATION = timedelta(minutes=5)

CONF_CLIENT_ID = "client_id"
CONF_INSTALLATION_ID = "installation_id"

# Registres de la VRC-W 450 Premium (« LWZx80 »), identifiés par balayage le 17/11/2026
REG_HUMIDITE = 2553        # humidité de l'air extrait, %
REG_TEMPERATURE = 2554     # température de l'air extrait, °C
REG_BYPASS = 2555          # état du bypass : 0 fermé, 1 ouvert (le mode n'est transmis par aucun registre)
REG_INTENSIF_RESTANT = 2557  # temps restant de l'intensif, min (0 hors intensif)
REG_FILTRE_JOURS = 2558    # jours avant le changement de filtre
REG_INTENSIF_DUREE = 2563  # durée réglée de l'intensif, min
REG_NIVEAU = 2564          # niveau APPLIQUÉ, 0-3 (intensif = 3) ; lecture seule (errorCode -32802)
REG_NIVEAU_BIS = 2565      # mode DEMANDÉ : 0-3 = niveau, 4 = programme horaire ; modifiable
REG_INCONNUS = (2556, 2559, 2560, 2561, 2562)  # toujours 0 (programme horaire… ?)
REGISTRES = list(range(2553, 2566))
