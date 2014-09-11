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

var drawOverlay = function (data, startHour, timelapseMinutes) {

  var adjTime = function (time) {
    var total = timelapseMinutes * 60 * 1000;
    return (time / (24 * 60)) * total;
  };

  var timeOffset = function (time) {
    var relativeTime = (Math.floor(time / 100) * 60 + (time % 100));
    var otime = relativeTime - (startHour * 60);
    if (otime < 0) {
      otime += 24 * 60;  // move time to after midnight
    }
    return otime;
  };

  return function () {

    d3.select("svg").remove();

    var layer = d3.select("div.overlay").append("svg:svg");
    var projection = this.getProjection();

    var transform = function (d) {
      d = new google.maps.LatLng(d.lat, d.lng);
      d = projection.fromLatLngToDivPixel(d);
      return d;
    };

    var time = layer.append('svg:text')
                    .attr('class', 'clock')
                    .attr('x', '80%').attr('y', '100px').attr('font-size', "64px")
                    .text("23:59");

    time.transition().duration(adjTime(24 * 60))
        .ease("linear")
        .tween("text", function (d) {
          var interpolate = d3.interpolate(0, 24 * 60);
          var format = d3.format("02d");
          return function (t) {
            var time = interpolate(t);
            var hours = (Math.floor(time / 60) + startHour) % 24;
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

    var colors = d3.scale.category20();
    var buses = routes.selectAll().data(function (d, i) {
      d.buses.forEach(function (v) { v['route'] = i; });
      return d.buses;
    }).enter().append("svg:circle");

    buses.transition()
      .ease("linear")
      .delay(function (d, i) {
        return adjTime(timeOffset(d.start));
      })
      .each("start", function () {
        d3.select(this)
          .attr("r", 4)
          .attr("fill", function (d, i) { return colors(d.route); })
          .attr("class", "bus");
      })
      .duration(function (d, i) {
        return adjTime(timeOffset(d.stop) - timeOffset(d.start));
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

var loadData = function (params) {
  var service = params['service'],
      startHour = parseInt(params['start'], 10) || 0,
      timelapseMinutes = parseInt(params['duration'], 10) || 0;

  var overlay = new google.maps.OverlayView();

  d3.json("data/" + service + ".json", function (data) {
    overlay.onAdd = function () {
      var layer = d3.select(this.getPanes().overlayLayer).selectAll("div.overlay")
                    .data([1]).enter().append("div").attr("class", "overlay");

    };
    overlay.draw = drawOverlay(data, startHour, timelapseMinutes);

    overlay.setMap(map);
  });

  return overlay;
};

var initialize = function () {
  var start = 18;
  var duration = 2;
  var params = $.deparam.fragment() || {service: "1", start: 10, duration: 10};

  $.getJSON('data/services.json').done(function (data) {
    d3.select('#service').selectAll().data(data)
      .enter().append("option")
      .attr("value", function (d) {
        return d.mnemo;
      })
      .text(function (d) {
        return d.mnemo;
      });

    $.each(params, function (k, v) {
      $('select[name="' + k + '"]').val(v);
    });
  });

  loadData(params);

  $('select').on('change', function () {
    var params = {};
    $.each($('#controls').serializeArray(), function (_, i) {
      params[i.name] = i.value;
    });
    $.bbq.pushState($('#controls').serialize(), 2);

    loadData(params);
  });
};

$(document).ready(initialize);
