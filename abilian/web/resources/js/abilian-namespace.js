/* Abilian namespace */
(function(Abilian, $) {

     /**
      * @define {?boolean} null if not set, false or true if explicitely set by
      * application. This variable should be set as soon as possible.
      */
     Abilian.DEBUG = null;

     /**
      *  @define {?string} locale to use. Set it as soon as possible. Defaults to 'en'.
      */
     Abilian.locale = 'en';

     /*
      * Abilian events. Listeners should be registered using
      * `jQuery(...).on(Abilian.events.event_name, ...)` rather than using
      * string value
      */
     Abilian.events = {};
     Abilian.events.appInit = 'abilian.app-init';

     /**
      * @define {Object} filled by custom code, holds information about current
      * logged user
      */
     Abilian.current_user = {
         anonymous: true
     };

     Abilian.init = function() {
         $(window).trigger(Abilian.events.appInit);
     };

})(window.Abilian = window.Abilian || {}, jQuery);
