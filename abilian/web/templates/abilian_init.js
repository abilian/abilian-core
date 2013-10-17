Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = {{ get_locale().language|tojson }};

bootbox.setDefaults({
    'locale': Abilian.locale
});

Abilian.init();
