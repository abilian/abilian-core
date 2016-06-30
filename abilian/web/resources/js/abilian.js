/* jshint camelcase: false */
(function (factory) {
  'use strict';
  require(['AbilianNS', 'jquery', 'Hogan'], factory);
}(function (Abilian, $, Hogan) {
  'use strict';

  var navbar = document.querySelector('nav.navbar-fixed-top');

  /**
   * Compensate scroll with navbar height if fixed navbar
   */
  function fixScroll() {
    var offset = navbar.clientHeight;
    scrollBy(0, -offset);
  }

  if (navbar) {
    if (location.hash) {
      /* fix scrolling when loading page with anchor */
      window.addEventListener('load', fixScroll);
    }
    window.addEventListener("hashchange", fixScroll);
  }

  /**
   * For form inputs: disable form submission on 'enter' key
   * We put this function in jQuery.fn so that it is callable on any $()
   * wrapped element.
   */
  $.fn.preventEnterKey = function () {
    return $(this).on('keypress', function (e) {
      if (e.keyCode == 13) {
        e.preventDefault();
      }
    });
  };

  /**
   * Prevent double form submit.
   */
  function reEnableSubmitControls() {
    var $elements = $('[data-prevent-double-submit]');
    $elements.each(function () {
      this.classList.remove('disabled');
      $(this).data('preventDoubleSubmit', false);
    });
  }

  Abilian.fn.prevent_double_submit = function () {
    $(document).on('click', '[type="submit"]', function (e) {
      var form = e.currentTarget.form;
      if (form.checkValidity !== undefined && !form.checkValidity()) {
        // HTML5 constraint API. form will not validate, so will not be
        // submitted: don't disable buttons.
        return;
      }
      var $elements = $(form.elements);
      $elements.each(function () {
        if (!this.classList.contains('disabled')) {
          this.classList.add('disabled');
          $(this).data('preventDoubleSubmit', true);
        }
      });
    });

    window.addEventListener('unload', reEnableSubmitControls);
  };
  Abilian.fn.onAppInit(Abilian.fn.prevent_double_submit);

  /**
   * This function is to be set on window.onbeforeprint.
   */
  Abilian.fn.before_print = function () {
    /* Firefox does not allow page-break inside fieldsets: for very long
     * fieldset bottom maybe below page footer... */
    $(document.body).find('fieldset').each(
        function () {
          $(this).replaceWith('<div class="fieldset">' + $(this).html() + '</div>');
        });
  };

  Abilian.fn.initWidgets = function () {
    $('.js-widget').each(Abilian.initJsWidget);

    $('[data-toggle="select2"]').each(function () {
      var el = $(this);
      el.select2({allowClear: !el.hasClass('required')});
    });

    $('[data-toggle="on-off"]').each(function () {
      var parent = this.parentNode;
      var $el = $(this);

      if (parent.tagName == 'LABEL') {
        $el.insertAfter(parent);
        parent = $(parent);
        if (parent.text().trim().length == 0) {
          parent.remove();
        }
      }
      $el.bootstrapSwitch();
    });

    $(".timepicker").timepicker()
        .on('click.timepicker',
            function (e) {
              e.preventDefault();
              $(this).timepicker('showWidget');
            }
        );

    datetimePickerSetup();
    $(document).trigger(Abilian.events.widgetsInitialized);
  };

  $(window).on(Abilian.events.appAfterInit,
      Abilian.fn.initWidgets);

  function datetimePickerSetup() {
    /* automatically concat datepicker + timepicker in hidden input */
    $('.datetimepicker').each(
        function () {
          var $self = $(this);
          var $datepicker = $('#' + this.id + '-date');
          var $timepicker = $('#' + this.id + '-time');

          $datepicker.parent().on(
              'changeDate',
              function updateDateTime(e) {
                $self.val($datepicker.val() + ' | ' + $timepicker.val());
              }
          );

          $timepicker.timepicker().on(
              'changeTime.timepicker',
              function updateDateTime(e) {
                $self.val($datepicker.val() + ' | ' + e.time.value);
              }
          );
        }
    );
  }

  function initLiveSearch() {
    var datasets = [];

    $(Abilian.api.search.object_types).each(
        function (idx, info) {
          var name = info[0].replace(/\./g, '-');
          var d = {
            name: name,
            remote: {
              url: Abilian.api.search.live,
              filter: function (response) {
                return response.results[info[0]] || [];
              },
              cache: false,
            },
            limit: 15,
            engine: Hogan,
            header: '<b><i>' + info[1] + '</i></b>',
            valueKey: 'name',
            template: '{{name}}',
          };
          datasets.push(d);
        });

    var search_box = $("#search-box");

    if (search_box.length == 0) {
      return;
    }

    if (datasets.length == 0) {
      search_box.attr('disabled', true);
      return;
    }

    search_box.typeahead(datasets)
        .on('typeahead:selected', function (e, data) {
          if (data.url) {
            e.preventDefault();
            document.location = data.url;
          }
        });

    // on enter key: go to search page
    var typeahead = search_box.data('ttView');
    typeahead.inputView.on(
        'enterKeyed',
        function (e) {
          search_box.get(0).form.submit();
        }
    );
    $('.tt-hint').addClass('form-control');
  }

  Abilian.fn.onAppInit(initLiveSearch);
}));
