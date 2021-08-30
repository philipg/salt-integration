function exec_poller(state_id) {
  $("#ajaxSpinnerImage").show();
  $.ajax({
    url: 'https://vg1o7v3fq3.execute-api.eu-west-2.amazonaws.com/prod/build/' + state_id + '/',
    type: "POST",
    headers: {"x-api-key": "4q7DaENfgm85jpDzG273G1GIMt2EJlqB8tZSt49q"},
    contentType: "application/json",
    success: function(data) {
        console.log(data)
        console.log("polling");
    },
    dataType: "json",
    complete: setTimeout(function() {exec_poller(state_id)}, 5000),
    timeout: 2000
  });
  return state_id
}

$(document).ready(function () {
    $("form").submit(function (event) {
      var API_URL = "https://vg1o7v3fq3.execute-api.eu-west-2.amazonaws.com/prod/build";

      var formData = {
        name: $("#name").val(),
        email: $("#email").val(),
        superheroAlias: $("#superheroAlias").val(),
      };
  
      $.ajax({
        type: "POST",
        url: API_URL,
        headers: {"x-api-key": "4q7DaENfgm85jpDzG273G1GIMt2EJlqB8tZSt49q"},
        data: JSON.stringify({'order_id': $('#orderid').val(), 'name': $('#name').val(), 'email': $('#email').val()}),
        contentType: "application/json",
        success: function(data){
          $("form").html(
            '<div class="alert alert-success">' + data.executionId + "</div>"
          );
          exec_poller(data.executionId)
          console.log(data)
        }
      }).done(function (data) {
        $("form").html(
          '<div class="alert alert-success">' + data.executionId + "</div>"
        );
        exec_poller(data.executionId)
        console.log(data);
      });
  
      event.preventDefault();
    });
  });
