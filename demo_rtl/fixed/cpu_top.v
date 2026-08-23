// =============================================================================
// ChipPilot AI Demo - Fixed Clean CPU Top Level Interconnect
// =============================================================================

module cpu_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] instr,
    output wire [31:0] dmem_addr,
    output wire [31:0] dmem_wdata,
    output wire        dmem_we,
    output wire [31:0] alu_out_test
);

    wire [3:0]  alu_opcode;
    wire        reg_we;
    wire [4:0]  rs1 = instr[19:15];
    wire [4:0]  rs2 = instr[24:20];
    wire [4:0]  rd  = instr[11:7];
    wire [31:0] rdata1;
    wire [31:0] rdata2;
    wire [31:0] alu_result;
    wire        alu_overflow;
    wire [7:0]  status_byte;

    // Submodule 1: Control Unit
    control_unit u_ctrl (
        .clk(clk),
        .rst_n(rst_n),
        .opcode(instr[6:0]),
        .alu_op(alu_opcode),
        .reg_we(reg_we),
        .mem_we(dmem_we),
        .status_out(status_byte)
    );

    // Submodule 2: Register File
    regfile u_regfile (
        .clk(clk),
        .rst_n(rst_n),
        .raddr1(rs1),
        .raddr2(rs2),
        .waddr(rd),
        .wdata(alu_result),
        .we(reg_we),
        .rdata1(rdata1),
        .rdata2(rdata2)
    );

    // Submodule 3: ALU
    alu u_alu (
        .a(rdata1),
        .b(rdata2),
        .opcode(alu_opcode),
        .result(alu_result),
        .overflow(alu_overflow)
    );

    assign dmem_addr = alu_result;
    assign dmem_wdata = rdata2;
    assign alu_out_test = alu_result;

endmodule
