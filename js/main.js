/* global d3, google */

var map = new google.maps.Map(d3.select("#map").node(), {
  zoom: 13,
  center: new google.maps.LatLng(55.9463, -3.2066),
  mapTypeId: google.maps.MapTypeId.SATELLITE,
  disableDefaultUI: true,
  scrollwheel: false,
  disableDoubleClickZoom: true,
  draggable: false,
});

d3.json("data/" + window.location.hash.substring(1) + "_route.json", function (data) {
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
          .x(function (d) { return transform(d).x; })
          .y(function (d) { return transform(d).y; })
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

      var colors = d3.scale.category20();
      var buses = routes.selectAll().data(function (d, i) {
        d.buses.forEach(function (v) { v['route'] = i; });
        return d.buses;
      }).enter()
          .append("svg:circle")
          .attr("r", 4)
          .attr("fill", function (d, i) { return colors(d.route); })
          .attr("class", "bus")
          .attr("transform", function (d) {
            return "translate(" + transform(d3.select(this.parentNode).datum().points[0]) + ")";
          });

      buses.transition()
        .ease("linear")
        .delay(function (d, i) {
          return adjTime(d.start);
        })
        .duration(function (d, i) {
          return adjTime(d.stop - d.start);
        })
        .attrTween("transform", function (d, i, a) {
          var path = d3.select(this.parentNode).select('path')[0][0];
          var l = path.getTotalLength();
          return function (t) {
            var p = path.getPointAtLength(t * l);
            return "translate(" + p.x + "," + p.y + ")";
          };
        })
        .transition().duration(2000).style("opacity", 0).remove();
    };
  };

  overlay.setMap(map);
});

