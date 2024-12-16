Le simulazioni si avviano creando un oggetto di tipo _Simulation2D_ definito dentro _Simulation2D.py_.
Dentro _main.py_ c'è un loop che fa partire alcune simulazioni variando la velocità della palla.

Ogni simulazione ha un indice (0, 1...), e i file relativi a quella simulazione vengono generati dentro una cartella di nome "Dynamic_Simulation_\<index>".

Per ogni simulazione vengono generati quattro file:
- **Dynamic_Simulation_\<index>_input.json:** contiene un dizionario con queste informazioni: "index", "density" "speed_x", "speed_y", "circle_impact_angle", ovvero l'indice della simulazione, la densità della palla, le velocità della palla lungo l'asse x e lungo l'asse y e l'angolo di impatto
- **\<index>_output_displacement.csv:** file in cui ogni riga ha questo formato: "\<node label>, \<displacement lungo asse x>, \<displacement lungo asse y>"
- **\<index>_output_displacement_external.csv:** file in cui ogni riga ha questo formato: "\<node label>, \<displacement lungo asse x>, \<displacement lungo asse y>", e sono presenti solo informazioni sui nodi sulla frontiera
- **\<index>_output_stress.csv:** file in cui ogni riga ha questo formato: "\<element label>, \<stress>"

La cartella 0 contiene un esempio di questi file.
