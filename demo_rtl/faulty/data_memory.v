// =============================================================================
// ChipPilot AI Demo - Data Memory Module
// =============================================================================

module data_memory (
    input  wire        clk,
    input  wire [31:0] addr,
    input  wire [31:0] wdata,
    input  wire        we,
    output wire [31:0] rdata
);

    reg [31:0] mem [255:0];

    always @(posedge clk) begin
        if (we) begin
            mem[addr[7:0]] <= wdata;
        end
    end

    assign rdata = mem[addr[7:0]];

endmodule
