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
    var RESIZE_MODES = {
        SCALE: 'scale',
        FIT: 'fit',
        CROP: 'crop'
    };

    var defaults = {
        width: 55,
        height: 55,
        resize_mode: 'FIT'
    };

    function ImageInput(node, options) {
        FileInput.call(this, node, $.extend({}, defaults, options));
        this.preview_node = node.find('.upload_preview').get(0);
        var $preview = $(this.preview_node);
        this.width = $preview.data('width') || options.width;
        this.height = $preview.data('height') || options.height;
        this.resize_mode = RESIZE_MODES[options.resize_mode]
            || RESIZE_MODES.FIT;
        // api.event.on(this.fileapi_node, 'change', this.changeImage.bind(this));
    }

    ImageInput.prototype = Object.create(FileInput.prototype);

    ImageInput.prototype.createFileNode = function(file) {
        var self = this,
            el = FileInput.prototype.createFileNode.call(self, file),
            image = api.Image(file);

        api.getInfo(file, function(err, infos) {
            if (err) {
                return;
            }

            var resize_fun = self['resize_' + self.resize_mode],
                preview;

            preview = resize_fun.call(self, image, infos);
            preview.get(function( err/**String*/, img/**HTMLElement*/ ) {
                el.prepend(img);
            });
        });
        return el;
    };

    /* resize mode functions */
    ImageInput.prototype.resize_scale = function(image, infos) {
        return image.resize(this.width, this.height, 'max');
    };


    ImageInput.prototype.resize_fit = function(image, infos) {
        var w_ratio = infos.width / this.width,
            h_ratio = infos.height / this.height,
            width, height, preview;

        if (w_ratio > h_ratio) {
            /* wider than taller: set target width to max width */
            width = this.width;
            height = Math.round(infos.height / w_ratio);
        } else {
            height = this.height;
            width = Math.round(infos.width / h_ratio);
        }

        return image.resize(width, height, 'preview');
    };


    ImageInput.prototype.resize_crop = function(image, infos) {
        return image.resize(this.width, this.height, 'preview');
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
