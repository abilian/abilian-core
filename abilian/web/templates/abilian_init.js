{%- set locale = get_locale() %}
(function($) {

$(document).ready(Abilian.init);

Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = {{ locale.language|tojson }};

bootbox.setDefaults({ 'locale': Abilian.locale });

/* generate script elements for JS locales */
function load_script(src) {
    var element = document.createElement("script");
    element.type = 'text/javascript';
    element.src = src;
    document.write(element.outerHTML);
    element = null;
};
{# load select2 locale file #}
load_script('{{ url_for('abilian_static', filename='select2/select2_locale_' + locale.language + '.js') }}');

{# bootstrap-datepicker locale #}
load_script('{{ url_for('abilian_static', filename='bootstrap-datepicker/js/locales/bootstrap-datepicker.' + locale.language + '.js') }}');

Abilian.datepicker_defaults = {
    'todayHighlight': true,
    'todayBtn': true,
    'language': {{ locale.language|tojson }},
    {#- first week day: for babel 0 == Monday, datetimepicker 0 == Sunday #}
    'weekStart': {{ ((locale.first_week_day + 1) % 7)|tojson }}
};
}(jQuery));
