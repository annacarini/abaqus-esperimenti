Le simulazioni si avviano creando un oggetto di tipo _Simulation2D_ definito dentro _Simulation2D.py_.
Dentro _main.py_ c'è un loop che fa partire alcune simulazioni variando la velocità della palla.

Ogni simulazione ha un indice (0, 1...), e i file relativi a quella simulazione vengono generati dentro una cartella con l'indice stesso come nome.

Per ogni simulazione vengono generati tre file:
- **\<index>_input.json:** contiene un dizionario con queste informazioni: "index", "density" "speed_x", "speed_y", ovvero l'indice della simulazione, la densità della palla, le velocità della palla lungo l'asse x e lungo l'asse y
- **\<index>_output_displacement.csv:** file in cui ogni riga ha questo formato: "\<node label>, \<displacement lungo asse x>, \<displacement lungo asse y>"
- **\<index>_output_stress.csv:** file in cui ogni riga ha questo formato: "\<element label>, \<stress>"

La cartella 0 contiene un esempio di questi file.
