require(["AbilianWidget", "widget.FileInput", "jquery", "FileAPI"], (
  Abilian,
  FileInput,
  $,
  api
) => {
  "use strict";

  /**
   * Image input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
   */
  const RESIZE_MODES = {
    SCALE: "scale",
    FIT: "fit",
    CROP: "crop",
  };

  const defaults = {
    width: 55,
    height: 55,
    resize_mode: "FIT",
  };

  function ImageInput(node, options) {
    FileInput.call(this, node, $.extend({}, defaults, options));
    this.preview_node = node.find(".upload_preview").get(0);
    const $preview = $(this.preview_node);
    this.width = $preview.data("width") || options.width;
    this.height = $preview.data("height") || options.height;
    this.resize_mode = RESIZE_MODES[options.resize_mode] || RESIZE_MODES.FIT;
    // api.event.on(this.fileapi_node, 'change', this.changeImage.bind(this));
  }

  ImageInput.prototype = Object.create(FileInput.prototype);

  ImageInput.prototype.createFileNode = function (file) {
    const self = this;
    const el = FileInput.prototype.createFileNode.call(self, file);
    const image = api.Image(file);

    api.getInfo(file, (err, infos) => {
      if (err) {
        console.log(err);
        return;
      }

      const resize_fun = self[`resize_${self.resize_mode}`];
      const preview = resize_fun.call(self, image, infos);
      preview.get((err /** String */, img /** HTMLElement */) => {
        if (err) {
          console.log(err);
          return;
        }
        el.prepend(img);
      });
    });
    return el;
  };

  /* resize mode functions */
  ImageInput.prototype.resize_scale = function (image, infos) {
    return image.resize(this.width, this.height, "max");
  };

  ImageInput.prototype.resize_fit = function (image, infos) {
    const w_ratio = infos.width / this.width;
    const h_ratio = infos.height / this.height;
    let width;
    let height;

    if (w_ratio > h_ratio) {
      /* wider than taller: set target width to max width */
      width = this.width;
      height = Math.round(infos.height / w_ratio);
    } else {
      height = this.height;
      width = Math.round(infos.width / h_ratio);
    }

    return image.resize(width, height, "preview");
  };

  ImageInput.prototype.resize_crop = function (image, infos) {
    return image.resize(this.width, this.height, "preview");
  };

  function createImageInput(options) {
    const element = $(this);
    const opts = $.extend({}, defaults, options);
    const widget = new ImageInput(element, opts);
    element.data("image-input", widget);
    return widget;
  }

  Abilian.registerWidgetCreator("imageInput", createImageInput);

  $.fn.imageInput = function (options) {
    const opts = $.extend({}, defaults, options);
    return this.each(function () {
      const node = $(this);
      let widget = node.data("image-input");
      if (widget === undefined) {
        widget = new ImageInput(node, opts);
        node.data("image-input", widget);
      }
      return widget;
    });
  };
});
