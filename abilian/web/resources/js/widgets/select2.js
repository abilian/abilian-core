(function(factory) {
    'use strict';
    require(['AbilianWidget', 'jquery'], factory);
}
 (function(Abilian, $) {
     'use strict';

     function tagsFormatter(tagsToReplace) {

         function replaceTag(tag) {
             return tagsToReplace[tag] || tag;
         }

         function safeTagsReplace(element) {
             var output =  element.text.replace(/&amp;/g, replaceTag);
             output =  output.replace(/&lt;/g, replaceTag);
             output =  output.replace(/&gt;/g, replaceTag);
             return output;
         }

         return safeTagsReplace;
     }

     var DEFAULT_PARAMS = {
         'containerCssClass': 'form-control'
     };


     function initSelect2(params) {
         var initParams = $.extend({}, DEFAULT_PARAMS, params);

         // replace the escaped html with proper tags
         // to be displayed in the select
         if('makeHtml' in params) {
             var tagsToReplace = {
                 '&amp;': '&',
                 '&lt;': '<',
                 '&gt;': '>'
             };

             //select2 parameters for formating function
             var formatter = tagsFormatter(tagsToReplace);
             initParams.formatResult = formatter;
             initParams.formatSelection = formatter;
         }

         this.select2(initParams);
     }

     Abilian.registerWidgetCreator('select2', initSelect2);


     var DEFAULT_AJAX_PARAMS = {
         dataType: 'json',
         quietMillis: 100,
         data: function (term, page) {
             return { q: term };
         },
         results: function (data, page) {
             return {results: data.results, more: false};
         }
     };

     function initSelect2Ajax(params) {
         var initParams = $.extend({}, DEFAULT_PARAMS, params),
             data = null;

         if (params.dataNodeId !== undefined) {
             data = JSON.parse($('#' + params.dataNodeId).html());

             initParams.initSelection = function(element, callback) {
                 if (data.values.length > 0) {
                     callback(data.values.length == 1 ? data.values[0]: data.values);
                 }
             };
         }

         if (params.ajax) {
             initParams.ajax = $.extend({}, DEFAULT_AJAX_PARAMS, params.ajax);
             if (!('minimumInputLength' in params)) {
                 initParams.minimumInputLength = 2;
             }
         } else if (!params.data || !params.tags) {
             // no ajax, no dataset provided: init would fail. This can happen
             // when this select2 data is changed later by external functions,
             // like an "on change" event handler on another input.
             initParams.data = [];
         }

         if (params.formatResult) {
             initParams.formatResult = function() {
                 var f = params.formatResult.split('.'),
                     formatter = window;

                 for (var i=0; i<f.length; i++) {
                     formatter = formatter[f[i]];
                 }

                 return formatter.apply(this, arguments);
             };
         }

         if (params.formatSelection) {
             initParams.formatSelection = function() {
                 var f = params.formatSelection.split('.'),
                     formatter = window;

                 for (var i=0; i<f.length; i++) {
                     formatter = formatter[f[i]];
                 }

                 return formatter.apply(this, arguments);
             };
         }

         this.select2(initParams);
     }

     Abilian.registerWidgetCreator('select2ajax', initSelect2Ajax);
 }));
