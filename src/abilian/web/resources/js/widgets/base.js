/* Abilian namespace */
define("AbilianWidget", ["AbilianNS", "jquery"], (Abilian, $) => {
  "use strict";

  /**
   * Initialize application parameters. Must be called when all resources are
   * loaded, but before any code is executed.
   */
  const widgetsCreators = {};

  /**
   * @param createFun: function(*params). Within function 'this' is set as
   * the item to widgetize wrapped with jQuery.
   */
  Abilian.registerWidgetCreator = (name, createFun) => {
    widgetsCreators[name] = createFun;
  };

  Abilian.getWidgetCreator = (name) => widgetsCreators[name];

  /*
   * Initialiaze a single element.
   */
  Abilian.initJsWidget = function () {
    const $this = $(this);
    const creatorName = $this.data("init-with");
    let params = $this.data("init-params");
    const creatorFunc = widgetsCreators[creatorName];

    if (creatorFunc === undefined) {
      throw new Error(`Unknown widget constructor: "${creatorName}"`);
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
