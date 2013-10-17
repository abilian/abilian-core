{%- set locale = get_locale() %}
(function($) {

$(document).ready(Abilian.init)

Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = {{ locale.language|tojson }};

bootbox.setDefaults({ 'locale': Abilian.locale });

/* load select2 locale file */
var element = document.createElement("script");
element.type = 'text/javascript';
element.src = '{{ url_for('abilian_static', filename='select2/select2_locale_' + locale.language) }}.js';
document.write(element.outerHTML);
element = null;

}(jQuery));
