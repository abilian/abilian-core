(function($) {
     /*
      * For form inputs: disable form submission on 'enter' key
      */
     $.fn.preventEnterKey = function() {
         return $(this).on('keypress', function(e) {                              
                            if (e.keyCode == 13) {
                                e.preventDefault();
                            }
                        });
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

     $(window).on(Abilian.events.appInit, initLiveSearch);

}(jQuery));
