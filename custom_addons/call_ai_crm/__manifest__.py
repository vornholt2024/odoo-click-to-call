{
    'name': 'Call AI CRM',
    'version': '1.0',
    'summary': 'Telefonie + KI Integration',

    'description': """
        Erweiterung von Odoo CRM um:
        - Click-to-Call Funktionen
        - Call Tracking
        - Call History Speicherung
        - Vorbereitung für KI-Analyse
    """,

    'author': 'Heinz-Jörg Vornholt',
    'category': 'CRM',

    'depends': [
        'base',
        'contacts'
    ],

    'data': [
        # Zugriffsrechte für die eigenen Datenmodelle
        'security/ir.model.access.csv',

        # Zeitgesteuerte Verarbeitung abgelaufener Soft-Locks
        'data/call_lock_cron.xml',

        # Erweiterung der Kontaktansicht
        'views/res_partner_views.xml',
    ],

    # Kleiner Browser-Baustein für die Übergabe der SIP-Adresse
    # an den unter Windows registrierten MicroSIP-Protokollhandler.
    'assets': {
        'web.assets_backend': [
            'call_ai_crm/static/src/js/microsip_call.js',
            'call_ai_crm/static/src/js/voice_note_recorder.js',
            'call_ai_crm/static/src/xml/voice_note_recorder.xml',
        ],
    },

    'installable': True,
    'application': True,

    'license': 'LGPL-3',
}