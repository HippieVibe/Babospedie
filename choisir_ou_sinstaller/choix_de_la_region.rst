Choix de la région
==================

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_temperature_ressentie_max_moyenne_ete.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_temperature_ressentie_min_moyenne_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_temperature_ressentie_moyenne_ete.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_temperature_ressentie_moyenne_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_pics_de_pollution_de_lair.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_qualite_de_lair.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_ratio_precipitations_evapotranspiration.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_ensolleillement_moyen_ete.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_ensolleillement_moyen_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_duree_moyenne_journee_ete.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_duree_moyenne_journee_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_vitesse_du_vent_ete.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_vitesse_du_vent_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_chutes_de_neige_hiver.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_pollution_des_sols.svg" />
  </figure>

.. raw:: html

  <figure>
    <embed type="image/svg+xml" src="../_static/images/carte_catastrophes_naturelles.svg" />
  </figure>

.. raw:: html

    <script>
      console.log("IM HERE FLAG FLAG");
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

      var maps = document.getElementsByTagName("embed");
      console.log("Found " + maps.length + " maps");

      for (var i = 0; i < maps.length; i++) {
        maps[i].onload = function () {
          var svg = this.getSVGDocument();
          var departements = svg.getElementsByClassName("departement");

          for (var j = 0; j < departements.length; j++) {
            departements[j].onclick = function () {
              this.classList.forEach((c) => {
                if (c.startsWith("z")) {
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
    </script>


Sources
-------

- `API open-source de météo <https://open-meteo.com>`_
- `Base de données GASPAR recensant les catastrophes naturelles <https://www.data.gouv.fr/fr/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/>`_
- `Base de données BASOL recensant les sols pollués <https://www.data.gouv.fr/en/datasets/base-des-sols-pollues/>`_
- `Bureau de Recherches Géologiques et Minières <https://www.brgm.fr/fr/actualite/communique-presse/nappes-eau-souterraine-au-1er-juin-2024>`_
