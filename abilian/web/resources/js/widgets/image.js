/* jshint camelcase: false */
(function($) {
    'use strict';
    /** 
     * Image input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
     */
    function ImageInput(node, options) {
        var self = this;
        self.root_node = node;
        self.preview_node = node.find('.upload_preview').get(0);
        self.fileapi_node = node.find('.js-fileapi-wrapper input').get(0);

        var $preview = $(self.preview_node);
        self.width = $preview.data('width') || options.width;
        self.height = $preview.data('height') || options.height;

        FileAPI.event.on(self.fileapi_node, 'change', function(evt) {
            self.changeImage(evt);
        });
    }

    ImageInput.prototype = {
        changeImage: function(evt) {
            var self = this;
            var file = FileAPI.getFiles(evt)[0];
            var image = FileAPI.Image(file);
            var preview = image.preview(self.width, self.height, 'max');
            preview.get(function( err/**String*/, img/**HTMLElement*/ ) {
                while (self.preview_node.firstChild) {                    
                    self.preview_node.removeChild(self.preview_node.firstChild);
                }
                self.preview_node.appendChild(img);
            });
        }
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

}(jQuery));
