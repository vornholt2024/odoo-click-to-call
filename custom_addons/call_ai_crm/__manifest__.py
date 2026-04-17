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

    'author': 'Jörg Vornholt',
    'category': 'CRM',

    'depends': [
        'base',
        'contacts'
    ],

    'data': [
        'security/ir.model.access.csv',   # 🔥 WICHTIG für Call History
        'views/res_partner_views.xml',
    ],

    'installable': True,
    'application': True,

    'license': 'LGPL-3',
}