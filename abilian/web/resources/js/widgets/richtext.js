(function (factory) {
  'use strict';
  require(['AbilianWidget'], factory);
}(function (Abilian) {
  'use strict';

  function initRichTextWidget(params) {
    var element = this;
    var name = this.attr['name'];
    var rows = parseInt(element.attr('rows')) || 10;
    var editor = null;

    function setupCkEditor($, ckeditor) {
      ckeditor.editorConfig = function (config) {
      };
      editor = ckeditor.replace(element.get(0));
    }

    require(['jquery', 'ckeditor'], setupCkEditor);
  }

  Abilian.registerWidgetCreator('richtext', initRichTextWidget);
}));
