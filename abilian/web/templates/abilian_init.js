/* -*- jinja2 -*- */
Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = 'fr'; {# FIXME: set locale from request/babel preferred locale #}

bootbox.setDefaults({
    'locale': Abilian.locale
});

Abilian.init();
