(function(factory) {
    'use strict';
    require(['AbilianWidget'], factory);
}
 (function(Abilian) {
     'use strict';


     function initRichTextWidget(params) {
         var element = this,
             name = this.attr['name'],
             rows = parseInt(element.attr('rows')) || 10,
             editor = null;

         function setupCkEditor($, ckeditor) {
             ckeditor.editorConfig = function(config) {};
             editor = ckeditor.replace(element.get(0));
         }

         require(['jquery', 'ckeditor'], setupCkEditor);
     }

     Abilian.registerWidgetCreator('richtext', initRichTextWidget);
 }));
