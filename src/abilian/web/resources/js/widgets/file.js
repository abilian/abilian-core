define("widget.FileInput", ["AbilianWidget", "jquery", "FileAPI", "Hogan"], (
  Abilian,
  $,
  api,
  Hogan
) => {
  "use strict";
  /**
   * File input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
   */
  const defaults = {
    fileItemTemplate: Hogan.compile(
      '<div id="{{ uid }}" class="file-item">\n' +
        '<span class="file-info">{{ name }} ({{ size }})</span> ' +
        '<a class="close" href="#">&times;</a>' +
        "\n</div>"
    ),
    progressTemplate:
      '<div class="progress">' +
      '<div class="progress-bar" role="progressbar" ' +
      '     aria-valuenow="0" aria-valuemin="0" ' +
      '     aria-valuemax="100" style="width: 0;">' +
      "</div>" +
      "</div>",
    inputTemplate: '<input type="hidden" name="{{ name }}" />',
    progressBarHeight: "0.2em",
  };

  function FileInput(node, options) {
    const self = this;
    this.currentlyUploaded = {};
    this.options = $.extend({}, defaults, options);
    this.form = node.parent("form");
    this.$input = node.find(".js-fileapi-wrapper input");
    this.$input.attr("disabled", null);
    this.rootNode = node;
    this.button = node.find(".js-fileapi-wrapper .btn-file");
    this.multiple = Boolean(this.$input.attr("multiple"));
    this.$input.attr("multiple", null);
    this.inputName = this.$input.attr("name");
    this.$input.attr("name", null);
    this.listNode = node.find(".selected-files");

    if (node.data("cloned")) {
      this.listNode.empty();
    } else {
      this.listNode.find(".file-item-existing").each(function () {
        self.setupExistingFileNode($(this));
      });
      this.listNode.find(".file-item-uploaded").each(function () {
        self.setupFileNode($(this));
      });
    }

    this.button.on("change", "input", this.addFiles.bind(this));

    this.form.on("submit", this.onFormSubmit.bind(this));
  }

  FileInput.prototype = {
    addFiles(evt) {
      const self = this;
      let files = api.getFiles(evt);

      if (!this.multiple) {
        this.listNode.empty();
        files = files.slice(0, 1);
      }

      $(files).each(function () {
        self.addFileNode(evt.target, this);
      });
    },

    setupExistingFileNode(node) {
      const button = node.find("button");
      const unwrappedButton = button.get(0);
      const deleted = button.data("deleted");

      if (!unwrappedButton) {
        return;
      }

      unwrappedButton.markerInputElement = $("<input>").attr({
        type: "hidden",
        name: button.data("name"),
        value: button.data("value"),
      });

      if (deleted) {
        node.append(unwrappedButton.markerInputElement);
      }

      button.on("click", { node: node }, this.onExistingNodeChange.bind(this));
    },

    setupFileNode(node) {
      node.find("a.close").on("click", this.removeFileNode.bind(this));
    },

    addFileNode(input, file) {
      const el = this.createFileNode(file);
      this.setupFileNode(el);
      this.listNode.append(el);
      this.triggerUpload(el, file);
    },

    triggerUpload(element, file) {
      const uid = api.uid(file);
      this.currentlyUploaded[uid] = true;

      api.upload({
        url: Abilian.api.upload.newFileUrl,
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": Abilian.csrf_token,
        },
        files: { file: file },
        progress: this.onFileProgress.bind(this),
        complete: this.onFileComplete.bind(this),
      });
    },

    removeFileNode(evt) {
      evt.preventDefault();
      $(evt.target).parent(".file-item").remove();
    },

    createFileNode(file) {
      const infos = this.getFileInfos(file);
      const el = $(this.options.fileItemTemplate.render(infos));
      const progress = $(this.options.progressTemplate).css({
        height: this.options.progressBarHeight,
      });

      el.append(progress);
      return el;
    },

    getElementForFile(file) {
      const uid = api.uid(file);
      return $(document.getElementById(uid));
    },

    getFileInfos(file) {
      return {
        name: this.sanitizeFilename(file.name),
        type: file.type,
        size: this.humanSize(file.size),
        uid: api.uid(file),
      };
    },

    onExistingNodeChange(evt) {
      const button = $(evt.target);
      const markerInputElement = evt.target.markerInputElement;
      const isActive = button.hasClass("active");

      button.toggleClass("active");

      if (isActive) {
        button.removeClass("btn-danger");
        button.addClass("btn-default");
        $(markerInputElement).remove();
      } else {
        button.removeClass("btn-default");
        button.addClass("btn-danger");
        button.parent(".file-item").append(markerInputElement);
      }
    },

    onFileProgress(evt, file, xhr, options) {
      const progress = (evt.loaded / evt.total) * 100;
      this.getElementForFile(file)
        .find(".progress-bar")
        .css({ width: `${progress}%` });
    },

    onFileComplete(err, xhr, file, options) {
      const $el = this.getElementForFile(xhr.currentFile);
      const uid = api.uid(xhr.currentFile);

      delete this.currentlyUploaded[uid];

      if (err) {
        $el.remove();
        alert("Echec de l'envoi du fichier!"); // FIXME: i18n
        return;
      }

      const $input = $("<input>").attr({
        type: "hidden",
        name: this.inputName,
      });
      const responseText = xhr.responseText;
      const result = JSON.parse(responseText);

      $el.find(".progress").remove();
      $input.val(result.handle);
      $el.append($input);
    },

    onFormSubmit(e) {
      if (Object.keys(this.currentlyUploaded).length > 0) {
        e.preventDefault();
        alert("Des fichiers sont en cours d'envoi"); // FIXME: i18n
      }
    },

    sanitizeFilename(filename) {
      return filename.replace(/\\/g, "/").replace(/.*\//, "");
    },

    humanSize(size) {
      let unit = "b";
      let divider = null;

      if (size > api.TB) {
        unit = "TB";
        divider = api.TB;
      } else if (size > api.GB) {
        unit = "GB";
        divider = api.GB;
      } else if (size > api.MB) {
        unit = "MB";
        divider = api.MB;
      } else if (size > api.KB) {
        unit = "KB";
        divider = api.KB;
      }

      if (divider) {
        size = (size / divider).toFixed(2);
      }

      return size.toString() + unit;
    },
  };

  function createFileInput(options) {
    const element = $(this);
    const widget = new FileInput(element, options);
    element.data("file-input", widget);
    return widget;
  }

  Abilian.registerWidgetCreator("fileInput", createFileInput);

  $.fn.fileInput = function (options) {
    return this.each(function () {
      const node = $(this);
      let widget = node.data("file-input");
      if (widget === undefined) {
        widget = new FileInput(node, options);
        node.data("file-input", widget);
      }
      return widget;
    });
  };

  return FileInput;
});
