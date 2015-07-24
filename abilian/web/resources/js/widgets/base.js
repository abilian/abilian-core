/* Abilian namespace */
(function(factory) {
    'use strict';
    define('AbilianWidget', ['AbilianNS', 'jquery'], factory);
}
(function(Abilian, $) {
    'use strict';

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
        var $this = $(this),
            creatorName = $this.data('init-with'),
            params = $this.data('init-params'),
            creatorFunc = widgetsCreators[creatorName];

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
    Abilian.events.widgetsInitialized = 'widgets-initiliazed';

    return Abilian;
}));
