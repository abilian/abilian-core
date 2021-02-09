require(["AbilianWidget", "jquery"], (Abilian, $) => {
  "use strict";

  function tagsFormatter(tagsToReplace) {
    function replaceTag(tag) {
      return tagsToReplace[tag] || tag;
    }

    function safeTagsReplace(element) {
      let output = element.text.replace(/&amp;/g, replaceTag);
      output = output.replace(/&lt;/g, replaceTag);
      output = output.replace(/&gt;/g, replaceTag);
      return output;
    }

    return safeTagsReplace;
  }

  const DEFAULT_PARAMS = {
    containerCssClass: "form-control",
  };

  function initSelect2(params) {
    const initParams = $.extend({}, DEFAULT_PARAMS, params);

    // replace the escaped html with proper tags
    // to be displayed in the select
    if ("makeHtml" in params) {
      const tagsToReplace = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
      };

      // select2 parameters for formating function
      const formatter = tagsFormatter(tagsToReplace);
      initParams.formatResult = formatter;
      initParams.formatSelection = formatter;
    }

    this.select2(initParams);
  }

  Abilian.registerWidgetCreator("select2", initSelect2);

  const DEFAULT_AJAX_PARAMS = {
    dataType: "json",
    quietMillis: 100,
    data(term, page) {
      return { q: term };
    },
    results(data, page) {
      return { results: data.results, more: false };
    },
  };

  function initSelect2Ajax(params) {
    const initParams = $.extend({}, DEFAULT_PARAMS, params);
    // let data = null;

    if (params.dataNodeId !== undefined) {
      const data = JSON.parse($(`#${params.dataNodeId}`).html());
      const values = data.values;

      initParams.initSelection = (element, callback) => {
        if (values.length > 0) {
          callback(values.length === 1 ? values[0] : values);
        }
      };
    }

    if (params.ajax) {
      initParams.ajax = $.extend({}, DEFAULT_AJAX_PARAMS, params.ajax);
      if (!("minimumInputLength" in params)) {
        initParams.minimumInputLength = 2;
      }
    } else if (!params.data || !params.tags) {
      // no ajax, no dataset provided: init would fail. This can happen
      // when this select2 data is changed later by external functions,
      // like an "on change" event handler on another input.
      initParams.data = [];
    }

    if (params.formatResult) {
      initParams.formatResult = function () {
        const f = params.formatResult.split(".");
        let formatter = window;

        for (let i = 0; i < f.length; i++) {
          formatter = formatter[f[i]];
        }

        return formatter.apply(this, arguments);
      };
    }

    if (params.formatSelection) {
      initParams.formatSelection = function () {
        const f = params.formatSelection.split(".");
        let formatter = window;

        for (let i = 0; i < f.length; i++) {
          formatter = formatter[f[i]];
        }

        return formatter.apply(this, arguments);
      };
    }

    this.select2(initParams);
  }

  Abilian.registerWidgetCreator("select2ajax", initSelect2Ajax);
});
