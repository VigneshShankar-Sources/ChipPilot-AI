// =============================================================================
// ChipPilot AI Demo - Faulty Control Unit
// Contains Bug 4: Unused registers and dangling internal nets
// =============================================================================

module control_unit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [6:0]  opcode,
    output reg  [3:0]  alu_op,
    output reg         reg_we,
    output reg         mem_we,
    output wire [7:0]  status_out
);

    // Bug 4: Unused registers and nets that consume area or trigger synthesis warnings
    reg [7:0]  unused_config_reg;
    wire [15:0] dangling_internal_wire;

    always @(*) begin
        case (opcode)
            7'b0110011: begin // R-type ALU
                alu_op = 4'b0111;
                reg_we = 1'b1;
                mem_we = 1'b0;
            end
            7'b0000011: begin // Load
                alu_op = 4'b0000;
                reg_we = 1'b1;
                mem_we = 1'b0;
            end
            7'b0100011: begin // Store
                alu_op = 4'b0000;
                reg_we = 1'b0;
                mem_we = 1'b1;
            end
            default: begin
                alu_op = 4'b0000;
                reg_we = 1'b0;
                mem_we = 1'b0;
            end
        endcase
    end

    assign status_out = 8'hA5;

endmodule
