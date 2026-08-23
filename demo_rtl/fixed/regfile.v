// =============================================================================
// ChipPilot AI Demo - Fixed Clean Register File
// Fix 3: Implemented asynchronous active-low reset initialization
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
    integer i;

    // Correct asynchronous reset handling
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 32; i = i + 1) begin
                registers[i] <= 32'd0;
            end
        end else if (we && waddr != 5'd0) begin
            registers[waddr] <= wdata;
        end
    end

    assign rdata1 = (raddr1 == 5'd0) ? 32'd0 : registers[raddr1];
    assign rdata2 = (raddr2 == 5'd0) ? 32'd0 : registers[raddr2];

endmodule
