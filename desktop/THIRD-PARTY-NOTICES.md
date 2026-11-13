# Composants tiers distribués avec DeckEdge

Le code propre à DeckEdge est sous licence MIT (LICENSE). Les composants suivants
conservent leurs licences ; ils ne sont pas couverts par la licence MIT de DeckEdge.

- LibreHardwareMonitorLib 0.9.6, sans modification, MPL-2.0.
  Sources exactes : https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/3d331e3370efb858411f19511373eff65a218701
  Une copie de ces sources est disponible dans `licenses/sources` du paquet.
  Les modules PawnIO intégrés conservent leur licence LGPL-2.1 ; leurs sources
  et instructions de reconstruction sont indiquées dans ce même dossier.
- Bibliothèques de support .NET : versions, licences et liens vers leurs sources
  dans `licenses/dotnet`. Elles sont redistribuées sans modification et peuvent
  être remplacées par des versions compatibles dans le dossier de DeckEdge.
- Microsoft WebView2 SDK 1.0.4314.35 : licence Microsoft incluse.
  Le Runtime WebView2 Evergreen est un prérequis Windows distinct ; l’installateur
  peut lancer son installation officielle si le Runtime manque.
- Python 3.14.9 : licence PSF et mentions dans `runtime/LICENSE.txt`.
- Modules Python : versions dans requirements.txt et PYTHON-PACKAGES.json,
  licences originales dans `runtime/Lib/site-packages/*.dist-info` et `licenses/python`.

Sources et licences originales sont conservées ; aucun composant tiers ne change
le nom de son auteur. DeckEdge n’est ni un produit Elgato, ni affilié à Elgato.
