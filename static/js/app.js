/* Listes déroulantes en cascade Région → Préfecture → Commune → Quartier
   et contrôle du passeport en temps réel (§8). */
(function () {
  "use strict";

  function remplir(select, options, valeurCourante) {
    select.innerHTML = '<option value="">---------</option>';
    options.forEach(function (o) {
      var opt = new Option(o.nom, o.id);
      if (String(o.id) === String(valeurCourante)) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function cascade(parent, enfant, url, parametre) {
    if (!parent || !enfant) return;
    parent.addEventListener("change", function () {
      if (!parent.value) { remplir(enfant, []); enfant.dispatchEvent(new Event("change")); return; }
      fetch(url + "?" + parametre + "=" + encodeURIComponent(parent.value))
        .then(function (r) { return r.json(); })
        .then(function (d) { remplir(enfant, d.options); enfant.dispatchEvent(new Event("change")); });
    });
  }

  document.querySelectorAll("[data-cascade-geo]").forEach(function (bloc) {
    var q = function (n) { return bloc.querySelector("[name$='" + n + "']"); };
    cascade(q("region"), q("prefecture"), "/geographie/prefectures/", "region");
    cascade(q("prefecture"), q("commune"), "/geographie/communes/", "prefecture");
    cascade(q("commune"), q("quartier"), "/geographie/quartiers/", "commune");
  });

  // --- Contrôle du passeport -------------------------------------------------
  var champ = document.querySelector("[data-controle-passeport]");
  if (champ) {
    var form = champ.form;
    var expiration = form.querySelector("[name$='date_expiration']");
    var zone = document.getElementById("controle-passeport");
    var minuteur;

    function controler() {
      if (!champ.value.trim()) { zone.innerHTML = ""; return; }
      var params = new URLSearchParams({ numero: champ.value, expiration: expiration ? expiration.value : "" });
      if (champ.dataset.pelerin) params.set("pelerin", champ.dataset.pelerin);
      fetch("/pelerins/controle-passeport/?" + params)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.alertes.length) {
            zone.innerHTML = d.statut
              ? '<div class="alert alert-success py-2 mb-0"><i class="bi bi-check-circle"></i> Passeport ' + d.statut_libelle.toLowerCase() + ', aucun doublon.</div>'
              : '<div class="text-success small"><i class="bi bi-check-circle"></i> Numéro non enregistré.</div>';
            return;
          }
          zone.innerHTML = d.alertes.map(function (a) {
            var lien = (a.titre === "DOUBLON DÉTECTÉ" && d.pelerin_existant)
              ? ' <a class="alert-link" href="/pelerins/' + d.pelerin_existant.id + '/">Voir le dossier</a>' : "";
            return '<div class="alert alert-' + a.niveau + ' py-2 mb-1"><strong>' + a.titre + "</strong> – " + a.message + lien + "</div>";
          }).join("");
        });
    }

    function differer() { clearTimeout(minuteur); minuteur = setTimeout(controler, 400); }
    champ.addEventListener("input", differer);
    if (expiration) expiration.addEventListener("change", controler);
  }
})();
