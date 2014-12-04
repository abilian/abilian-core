/* Abilian namespace */
(function(Abilian, $) {

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

    /*
     * Initialiaze a single element.
     */
    Abilian.initJsWidget = function() {
        var $this = $(this);
        var creatorName = $this.data('init-with');
        var params = $this.data('init-params');

        if (!(params instanceof Array)) {
            params = new Array(params);
        }
        widgetsCreators[creatorName].apply($this, params);
    };

    /*
     * Custom events
     */
    Abilian.events.widgetsInitialized = 'widgets-initiliazed';

    Abilian.registerWidgetCreator(
        'select2',
        function(params) {
            var initParams = {
                'containerCssClass': 'form-control'
            };
            $.extend(initParams, params);
            this.select2(initParams);
        });

})(window.Abilian = window.Abilian || {}, jQuery);
