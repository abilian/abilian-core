/* Abilian namespace */
/* jshint camelcase: false */

function setupAbilian($) {
  'use strict';

  var Abilian = window.Abilian = window.Abilian || {};
  var initialized = false;

  /**
   * @define {?boolean} null if not set, false or true if explicitely set by
   * application. This variable should be set as soon as possible.
   */
  Abilian.DEBUG = null;

  /**
   *  @define {?string} locale to use. Set it as soon as possible. Abilian's
   *  default templates and scripts set it based on locale from user
   *  preferences or negociated by HTTP request.  Defaults to 'en'.
   */
  Abilian.locale = 'en';

  /**
   * Abilian events. Listeners should be registered using
   * `jQuery(...).on(Abilian.events.event_name, ...)` rather than using
   * string value
   */
  Abilian.events = {};
  Abilian.events.appInit = 'abilian.app-init';
  Abilian.events.appAfterInit = 'abilian.app-after-init';

  /**
   * CSRF field name to use, if CSRF is used
   */
  Abilian.csrf_fieldname = '';

  /**
   * CSRF token to use, if defined.
   */
  Abilian.csrf_token = '';

  /**
   * Abilian remote API
   */
  Abilian.api = {};

  /**
   * Abilian fonctions. Use this to register convenient functions
   */
  Abilian.fn = {};

  /**
   * Shortcut to register a function that must execute when application is
   * initialized. This is the preferred way to register init handlers.
   */
  Abilian.fn.onAppInit = function (callback) {
    if (!initialized) {
      $(window).on(Abilian.events.appInit, callback);
    } else {
      callback();
    }
  };

  /**
   * @define {Object} filled by custom code, holds information about current
   * logged user
   */
  Abilian.current_user = {
    anonymous: true,
  };

  Abilian.init = function () {
    initialized = true;
    $(window).trigger(Abilian.events.appInit);
    $(window).trigger(Abilian.events.appAfterInit);
  };

  return Abilian;
}

define('AbilianNS', ['jquery'], setupAbilian);
