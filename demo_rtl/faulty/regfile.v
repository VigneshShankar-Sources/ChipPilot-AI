// =============================================================================
// ChipPilot AI Demo - Faulty Register File Module
// Contains Bug 3: Missing asynchronous reset handling in sequential logic
// =============================================================================

module regfile (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [4:0]  raddr1,
    input  wire [4:0]  raddr2,
    input  wire [4:0]  waddr,
    input  wire [31:0] wdata,
    input  wire        we,
    output wire [31:0] rdata1,
    output wire [31:0] rdata2
);

    reg [31:0] registers [31:0];

    // Bug 3: Sensitivity list and body ignore rst_n! Registers power up in undefined state.
    always @(posedge clk) begin
        if (we && waddr != 5'd0) begin
            registers[waddr] <= wdata;
        end
    end

    assign rdata1 = (raddr1 == 5'd0) ? 32'd0 : registers[raddr1];
    assign rdata2 = (raddr2 == 5'd0) ? 32'd0 : registers[raddr2];

endmodule
