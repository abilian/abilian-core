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

         /* file input */
         $(document)
             .on('change', '.btn-file :file', function() {
                 var input = $(this),
                 numFiles = input.get(0).files ? input.get(0).files.length : 1,
                 label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
                 input.trigger('fileselect', [numFiles, label]);
             });
         $('.btn-file :file')
             .on('fileselect', function(event, numFiles, label) {
                 var input = $(this).parents('.input-group').find(':text'),
			     log = numFiles > 1 ? numFiles + ' files selected' : label;
			 
			     if( input.length ) {
				     input.val(log);
			     }
             });
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
         var datasets = [
             { name: 'documents',
               remote: '/search/live?type=documents&q=%QUERY',
               limit: 15,
               engine: Hogan,
               header: '<b><i>Documents</i></b>',
               template: '<img src="{{icon}}" width="16" height="16" /> {{value}}'
             }
         ];
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
