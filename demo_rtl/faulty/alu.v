// =============================================================================
// ChipPilot AI Demo - Faulty ALU Module
// Contains:
//   - Bug 1: Incomplete case statement -> Inferred 32-bit latch for 'result'
//   - Bug 2: Deep unpipelined cascading multiplication-shift -> Timing Setup Violation
// =============================================================================

module alu (
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [3:0]  opcode,
    output reg  [31:0] result,
    output wire        overflow
);

    // Bug 1: Missing 'default:' branch in combinational case statement
    // Bug 2: Critical timing path (Cascading 32x32 multiply and barrel shift in single cycle)
    always @(*) begin
        case (opcode)
            4'b0000: result = a + b;
            4'b0001: result = a - b;
            4'b0010: result = a & b;
            4'b0011: result = a | b;
            4'b0100: result = a ^ b;
            4'b0101: result = a << b[4:0];
            4'b0110: result = a >> b[4:0];
            4'b0111: result = (a * b) ^ (a << b[4:0]) + (b * 32'h045C3); // Deep Combinational Delay
            // Intentionally missing default case! Causes latch inference.
        endcase
    end

    assign overflow = (opcode == 4'b0000) && ((a[31] == b[31]) && (result[31] != a[31]));

endmodule
