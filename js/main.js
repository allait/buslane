/* global d3, google */

var map = new google.maps.Map(d3.select("#map").node(), {
  zoom: 13,
  center: new google.maps.LatLng(55.9463, -3.2066),
  mapTypeId: google.maps.MapTypeId.SATELLITE,
  disableDefaultUI: true,
  scrollwheel: false,
  disableDoubleClickZoom: true,
});

d3.json("service1.json", function(data) {
  var overlay = new google.maps.OverlayView();

  overlay.onAdd = function () {
    var adjTime = function (time) {
      var total = 5 * 60 * 1000;
      return (time / (24 * 60)) * total;
    };

    var layer = d3.select(this.getPanes().overlayLayer)
                  .append("div").attr("class", "overlay")
                    .append("svg:svg");

    overlay.draw = function () {
      var projection = this.getProjection();

      var transform = function (d) {
        d = new google.maps.LatLng(d.lat, d.lng);
        d = projection.fromLatLngToDivPixel(d);
        return d;
      };

      var time = layer.append('svg:text')
                      .attr('class', 'clock')
                      .attr('x', '50%').attr('y', '100px').attr('font-size', "64px")
                      .text("23:59");

      time.transition().duration(adjTime(24 * 60))
          .ease("linear")
          .tween("text", function (d) {
            var interpolate = d3.interpolate(1, 24 * 60);
            var format = d3.format("02d");
            return function (t) {
              var time = interpolate(t);
              var hours = Math.floor(time / 60) % 24;
              var minutes = Math.floor(time % 60);
              this.textContent = format(hours) + ':' + format(minutes);
            };
          });

      var routes = layer.selectAll().data(data).enter()
                        .append("svg:g").attr("class", "route");

      var line = d3.svg.line()
          .x(function(d) { return transform(d).x; })
          .y(function(d) { return transform(d).y; })
          .interpolate("linear");

      var route_line = routes.selectAll()
          .data(function (d) { return [d.points]; }).enter()
          .append("svg:path").attr("d", line);

      var marker = routes.selectAll()
          .data(function (d) { return d.points; })
        .enter().append("svg:circle")
          .attr("r", 3)
          .attr("cx", function (d) { return transform(d).x; })
          .attr("cy", function (d) { return transform(d).y; });
    };
  };

  overlay.setMap(map);
});

