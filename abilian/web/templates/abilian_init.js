{%- set locale = get_locale() %}
(function($) {

$(document).ready(Abilian.init);
window.onbeforeprint = Abilian.fn.before_print;

Abilian.DEBUG = {{ config.DEBUG|tojson }};
Abilian.locale = {{ locale.language|tojson }};


{%- set indexing_svc = app.services['indexing'] %}
Abilian.api.search = {
    'live': {{ url_for('search.live')|tojson }} + '?q=%QUERY',
    'object_types': {{ indexing_svc.searchable_object_types()|tojson }}
};

/* set up various libraries */

bootbox.setDefaults({ 'locale': Abilian.locale });

{#- load select2 locale file #}
Abilian.fn.loadScript('{{ url_for('abilian_static', filename='select2/select2_locale_' + locale.language + '.js') }}');

{#- bootstrap-datepicker locale #}
Abilian.fn.loadScript('{{ url_for('abilian_static', filename='bootstrap-datepicker/js/locales/bootstrap-datepicker.' + locale.language + '.js') }}');

$.extend(
    $.fn.datepicker.defaults,
    { 'todayHighlight': true,
      'todayBtn': true,
      'language': {{ locale.language|tojson }},
      'format': {{ locale.date_formats['short']|babel2datepicker|tojson }},
      {#- first week day: for babel 0 == Monday, datetimepicker 0 == Sunday #}
      'weekStart': {{ ((locale.first_week_day + 1) % 7)|tojson }}
    });

{#- timepicker: set 12/24 time #}
{%- set short_time = locale.time_formats['short'].format %}
$.extend(
    $.fn.timepicker.defaults,
    { 'showMeridian': {{ ('%(h)s' in short_time or '%(K)s' in short_time)|tojson }} 
    });

if (window.FileAPI) {
    window.FileAPI = $.extend(
        window.FileAPI,
        { debug: false   // debug mode, see Console
          , cors: false    // if used CORS, set `true`
          , media: false   // if used WebCam, set `true`
          , staticPath: {{ url_for('abilian_static', filename='fileapi/')|tojson }} // path to '*.swf'
          , flashUrl:  {{ url_for('abilian_static', filename='fileapi/FileAPI.flash.swf')|tojson }}
          , flashImageUrl:  {{ url_for('abilian_static', filename='fileapi/FileAPI.flash.image.swf')|tojson }}
          , flashWebcamUrl:  {{ url_for('abilian_static', filename='fileapi/FileAPI.flash.camera.swf')|tojson }}
        });
}


}(jQuery));
