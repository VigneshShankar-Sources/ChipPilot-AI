read_verilog D:\project\Portfolio\eda_workspace\cpu_top_synth.v
link_design cpu_top
read_sdc D:\project\Portfolio\eda_workspace\default.sdc
report_checks -path_delay max -fields {slew cap input nets fanout} -digits 4
report_worst_slack -max
