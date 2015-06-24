/* jshint camelcase: false */
(function(factory) {
    'use strict';
    require(['AbilianWidget', 'widget.FileInput', 'jquery', 'FileAPI'], factory);
}
(function(Abilian, FileInput, $, api) {
    'use strict';
    /**
     * Image input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
     */
    var defaults = {
        width: 55,
        height: 55
    };

    function ImageInput(node, options) {
        FileInput.call(this, node, $.extend({}, defaults, options));
        this.preview_node = node.find('.upload_preview').get(0);
        var $preview = $(this.preview_node);
        this.width = $preview.data('width') || options.width;
        this.height = $preview.data('height') || options.height;

        // api.event.on(this.fileapi_node, 'change', this.changeImage.bind(this));
    }

    ImageInput.prototype = Object.create(FileInput.prototype);

    ImageInput.prototype.createFileNode = function(file) {
        var el = FileInput.prototype.createFileNode.call(this, file),
            image = api.Image(file),
            preview = image.preview(this.width, this.height, 'max');

        preview.get(function( err/**String*/, img/**HTMLElement*/ ) {
            el.prepend(img);
        });

        return el;
    };

    function createImageInput(options) {
        var element = $(this),
            opts = $.extend({}, defaults, options),
            widget = new ImageInput(element, opts);
        element.data('image-input', widget);
        return widget;
    }
    Abilian.registerWidgetCreator('imageInput', createImageInput);

    $.fn.imageInput = function(options) {
        var opts = $.extend({}, defaults, options);
        return this.each(
            function() {
                var node = $(this);
                var widget = node.data('image-input');
                if (widget === undefined) {
                    widget = new ImageInput(node, opts);
                    node.data('image-input', widget);
                }
                return widget;
        });
    };

}));
