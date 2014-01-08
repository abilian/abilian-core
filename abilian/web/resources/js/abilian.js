(function($) {
     /**
      * For form inputs: disable form submission on 'enter' key
      * We put this function in jQuery.fn so that it is callable on any $()
      * wrapped element.
      */
     $.fn.preventEnterKey = function() {
         return $(this).on('keypress', function(e) {                              
                            if (e.keyCode == 13) {
                                e.preventDefault();
                            }
                        });
     };


    /**
     * Prevent double form submit.
     */
    Abilian.fn.prevent_double_submit = function () {
        $(document).on('click', '[type="submit"]', function(e) {
            var $elements = $(e.target.form.elements);
            $elements.addClass('disabled');
        });
    };
    Abilian.fn.onAppInit(Abilian.fn.prevent_double_submit);

     /**
      * This function is to be set on window.onbeforeprint.
      */
     Abilian.fn.before_print = function () {
         /* Firefox does not allow page-break inside fieldsets: for very long
          * fieldset bottom maybe below page footer... */
         $(document.body).find('fieldset').each(
             function() {
                 $(this).replaceWith('<div class="fieldset">' + $(this).html() + '</div>');
             });         
     };


     Abilian.fn.init_widgets = function() {
         $('[data-toggle="select2"]').select2();

         $(".timepicker").timepicker()
            .on('click.timepicker',
                function(e) {
                    e.preventDefault();
                    $(this).timepicker('showWidget');
                }
               );

         datetimePickerSetup();

         /* file / image input */
         $('.file-input').fileInput();
         $('.image-input').imageInput();
     };
     Abilian.fn.onAppInit(Abilian.fn.init_widgets);

     function datetimePickerSetup() {
         /* automatically concat datepicker + timepicker in hidden input */
         $('.datetimepicker').each(
             function() {
                 var $self = $(this);
                 var $datepicker = $('#'+ this.id + '-date');
                 var $timepicker = $('#'+ this.id + '-time');
                 
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
     };

     function initLiveSearch() {
         var datasets = []

         $(Abilian.api.search.object_types).each(
             function(idx, info) {
                 var name = info[0].replace(/\./g, '-');
                 var d = {
                     name: name,
                     remote: {
                         url: Abilian.api.search.live,
                         filter: function(response) {
                             return response.results[info[0]] || []
                         },
                         cache: false
                     },
                     limit: 15,
                     engine: Hogan,
                     header: '<b><i>' + info[1] + '</i></b>',
                     valueKey: 'name',
                     template: '{{name}}'
                 }
                 datasets.push(d);
             });

         var search_box = $("#search-box");
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
             function(e) { search_box.get(0).form.submit(); }
         );
         $('.tt-hint').addClass('form-control');
     }

     Abilian.fn.onAppInit(initLiveSearch);

}(jQuery));
