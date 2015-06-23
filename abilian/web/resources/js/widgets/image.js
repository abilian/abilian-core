/* jshint camelcase: false */
(function(factory) {
    'use strict';
    require(['widget.FileInput', 'jquery', 'FileAPI', 'Hogan'], factory);
}
(function(FileInput, $, api, Hogan) {
    'use strict';
    /**
     * Image input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
     */
    var defaults = {
        width: 120,
        height: 12
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

    $.fn.imageInput = function(options) {
        var defaults = { width: 120, height: 120 };
        var opts = $.extend(defaults, options);
        return this.each(
            function() {
                var node = $(this);
                var input = node.data('image-input');
                if (input === undefined) {
                    input = new ImageInput(node, opts);
                    node.data('image-input', input);
                }
                return input;
        });
    };

}));
