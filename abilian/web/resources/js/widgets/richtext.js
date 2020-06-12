require(["AbilianWidget"], function(Abilian) {
  "use strict";

  function initRichTextWidget(params) {
    var element = this;
    // var name = this.attr["name"];
    // var rows = parseInt(element.attr("rows")) || 10;
    // var editor = null;

    var config = {};

    var profile = this.attr("data-profile");
    console.log(profile);

    if (profile === "minimal") {
      config.entities = false;

      config.skin = "moono";

      config.extraPlugins = ["autolink", "bootstrapVisibility"];
      config.extraPlugins = config.extraPlugins.join(",");

      config.toolbar = [
        {
          name: "basicstyles",
          items: ["Bold", "Italic", "Underline", "-", "RemoveFormat"],
        },
        {
          name: "paragraph",
          items: ["NumberedList", "BulletedList"],
        },
      ];
      // Set the most common block elements.
      config.format_tags = "p;h1;h2;h3;pre";

      // Simplify the dialog windows.
      config.removeDialogTabs = "image:advanced;link:advanced";

      config.allowedContent = {
        a: { attributes: ["!href", "title"] },
        abbr: { attributes: ["title"] },
        acronym: { attributes: ["title"] },
        b: {},
        blockquote: { attributes: ["title"] },
        br: {},
        code: { attributes: ["title"] },
        em: {},
        i: {},
        li: {},
        ol: { attributes: ["title"] },
        strong: {},
        ul: { attributes: ["title"] },
        h1: {},
        h2: {},
        h3: {},
        h4: {},
        h5: {},
        h6: {},
        p: { attributes: ["style"], styles: ["text-align"] },
        u: {},
        img: { attributes: ["!src", "alt", "title"] },
      };
    }

    function setupCkEditor($, ckeditor) {
      ckeditor.replace(element.get(0), config);
    }

    require(["jquery", "ckeditor"], setupCkEditor);
  }

  Abilian.registerWidgetCreator("richtext", initRichTextWidget);
});
