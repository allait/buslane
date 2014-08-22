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

  overlay.onAdd = function() {
    var layer = d3.select(this.getPanes().overlayLayer).append("div").attr("class", "stations");

    overlay.draw = function() {
      var projection = this.getProjection();
      var transform = function (d) {
        d = new google.maps.LatLng(d.lat, d.lng);
        d = projection.fromLatLngToDivPixel(d);

        return d;
      };

      var setPoint = function (d) {
        d = transform(d);
        return d3.select(this)
              .style("left", (d.x-20) + "px")
              .style("top", (d.y-20) + "px");
      };

      var routes = layer.selectAll("div").data(data).enter().append("div").attr("class", "service");

      var line = d3.svg.line()
          .x(function(d) { return transform(d).x; })
          .y(function(d) { return transform(d).y; })
          .interpolate("linear");

      var route_line = routes.selectAll()
          .append("svg:svg")
          .append("svg:path")
          .data(function (d) { return [d.points]; })
              .attr("d", line);

      var marker = routes.selectAll()
          .data(function (d) { return d.points; })
        .enter().append("svg:svg")
          .each(setPoint);

      marker.append("svg:circle")
          .attr("r", 4.5)
          .attr("cx", 20)
          .attr("cy", 20);
    };
  };

  overlay.setMap(map);
});

