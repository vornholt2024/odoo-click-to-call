{
    'name': 'Call AI CRM',
    'version': '1.0',
    'summary': 'B2B Click-to-Call und KI-gestützte Gesprächsnachbearbeitung',

    'description': """
        Erweiterung der Odoo-Kontaktverwaltung zur Unterstützung
        der B2B-Telefonakquise mit Click-to-Call, Gesprächsprotokollierung,
        Anrufhistorie, Wiedervorlagenverwaltung und 
        KI-gestützter Verarbeitung von Voice Notes. 
        Die fachliche Klassifikation erfolgt regelbasiert; 
        vorgeschlagene Ergebnisse werden vor der Speicherung durch 
        den Mitarbeiter geprüft und bestätigt.
    """,

    'author': 'Heinz-Jörg Vornholt',
    'category': 'CRM',

    'depends': [
        'base',
        'contacts',
        'mail'
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