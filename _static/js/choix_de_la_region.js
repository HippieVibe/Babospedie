function toggle_hatch(departement) {
  var hatch_removed = false;
  departement.classList.forEach((c) => {
    if (c.startsWith("hatch-")) {
      departement.classList.remove(c);
      hatch_removed = true;
    }
  });

  if (!hatch_removed) {
    departement.classList.forEach((c) => {
      if (c.startsWith("color-")) {
        var color_id = c.split("-")[1];
        departement.classList.add("hatch-" + color_id);
      }
    });
  }
}

function toggle_in_hatch_list(departement_class) {
  var existing_hatch_list = localStorage.getItem("hatch_list");

  if (existing_hatch_list === null) {
    localStorage.setItem("hatch_list", departement_class);
  } else {
    var hatch_list_array = existing_hatch_list.split(",");
    var hatch_index = hatch_list_array.indexOf(departement_class);

    if (hatch_index > -1) {
      // Remove entry from the array
      hatch_list_array.splice(hatch_index, 1);
    } else {
      hatch_list_array.push(departement_class);
    }

    localStorage.setItem("hatch_list", hatch_list_array);
  }
}

function main() {
  var maps = document.getElementsByTagName("embed");

  var existing_hatch_list = localStorage.getItem("hatch_list");
  if (existing_hatch_list !== null) {
    existing_hatch_list = existing_hatch_list.split(",");
  } else {
    existing_hatch_list = [];
  }

  for (var i = 0; i < maps.length; i++) {
    maps[i].onload = function () {
      var svg = this.getSVGDocument();
      var departements = svg.getElementsByClassName("departement");

      for (var j = 0; j < departements.length; j++) {
        departements[j].classList.forEach((c) => {
          if (c.startsWith("z") && existing_hatch_list.includes(c)) {
            toggle_hatch(departements[j]);
          }
        });

        departements[j].onclick = function () {
          this.classList.forEach((c) => {
            if (c.startsWith("z")) {
              toggle_in_hatch_list(c);

              for (var k = 0; k < window.frames.length; k++) {
                var targets =
                  window.frames[k].document.getElementsByClassName(c);
                for (var l = 0; l < targets.length; l++) {
                  toggle_hatch(targets[l]);
                }
              }
            }
          });
        };
      }
    };
  }
}
document.addEventListener("DOMContentLoaded", main, false);
