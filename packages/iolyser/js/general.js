
$(document).ready(function(){
    var slider = $("input.slider").slider();
    getSensor();
    setInterval(getSensor, 500);
});


function getSensor() {
  string = "";
  for (i = 1; i <= 8; i++) {
    string = string + $("#sens"+i).val();
  }

  $.ajax({
    url: "/status?" + string
  })
    .done(function( data ) {
      for (i = 0; i <= 7; i++) {
        j = i + 1;
        $("#sensor" + j).html(data[i])
      }
  });
}

function setSpeed(mot,speed) {

  speed = speed * $("#mot"+ mot).val()
  $.ajax({
    url: "/mot?" + mot + "?" + speed
  });


}
