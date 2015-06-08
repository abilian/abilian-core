/* Abilian namespace */
(function(factory) {
    'use strict';
    require(['AbilianNS', 'jquery'], factory);
}
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

            // replace the escaped html with proper tags
            // to be displayed in the select
            if('makeHtml' in params){

                var tagsToReplace = {
                    '&amp;': '&',
                    '&lt;': '<',
                    '&gt;': '>'
                };

                function replaceTag(tag) {
                    return tagsToReplace[tag] || tag;
                }

                function safe_tags_replace(element) {
                    var output =  element.text.replace(/&amp;/g, replaceTag);
                    output =  output.replace(/&lt;/g, replaceTag);
                    output =  output.replace(/&gt;/g, replaceTag);
                    return output
                }
                //select2 parameters for formating function
                initParams['formatResult'] = safe_tags_replace;
                initParams['formatSelection'] = safe_tags_replace;
            }

            $.extend(initParams, params);
            this.select2(initParams);
        });

}));
