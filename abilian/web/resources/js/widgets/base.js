/* Abilian namespace */
define("AbilianWidget", ["AbilianNS", "jquery"], function(Abilian, $) {
  "use strict";

  /**
   * Initialize application parameters. Must be called when all resources are
   * loaded, but before any code is executed.
   */
  var widgetsCreators = {};

  /**
   * @param createFun: function(*params). Within function 'this' is set as
   * the item to widgetize wrapped with jQuery.
   */
  Abilian.registerWidgetCreator = function(name, createFun) {
    widgetsCreators[name] = createFun;
  };

  Abilian.getWidgetCreator = function(name) {
    return widgetsCreators[name];
  };

  /*
   * Initialiaze a single element.
   */
  Abilian.initJsWidget = function() {
    var $this = $(this);
    var creatorName = $this.data("init-with");
    var params = $this.data("init-params");
    var creatorFunc = widgetsCreators[creatorName];

    if (creatorFunc === undefined) {
      throw new Error('Unknown widget constructor: "' + creatorName + '"');
    }

    if (!(params instanceof Array)) {
      params = new Array(params);
    }

    creatorFunc.apply($this, params);
  };

  /*
   * Custom events
   */
  Abilian.events.widgetsInitialized = "widgets-initiliazed";

  return Abilian;
});
