'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { useMemo } from 'react';

interface MatrixItem {
    g: number;
    o: number;
    modes: any[];
}

interface RiskMatrixProps {
    data: any[]; // RPN ranking items
}

export function RiskMatrix({ data }: RiskMatrixProps) {
    // 10x10 matrix (1-10 scale)
    const cells = useMemo(() => {
        const matrix: MatrixItem[][] = Array.from({ length: 10 }, () =>
            Array.from({ length: 10 }, () => ({ g: 0, o: 0, modes: [] }))
        );

        data?.forEach(item => {
            const gIdx = item.gravity - 1;
            const oIdx = item.occurrence - 1;
            if (gIdx >= 0 && gIdx < 10 && oIdx >= 0 && oIdx < 10) {
                const cell = matrix[oIdx]![gIdx]!;
                cell.modes.push(item);
                cell.g = item.gravity;
                cell.o = item.occurrence;
            }
        });

        return matrix;
    }, [data]);

    const getCellColor = (cell?: MatrixItem) => {
        if (!cell || cell.modes.length === 0) return 'bg-background hover:bg-muted/50';

        // Use the maximum RPN in this cell for coloring to highlight highest risk
        const maxRpn = Math.max(...cell.modes.map(m => m.rpn_value || 0));

        if (maxRpn >= 200) return 'bg-red-500 text-white hover:bg-red-600';
        if (maxRpn >= 100) return 'bg-orange-400 text-white hover:bg-orange-500';
        if (maxRpn >= 50) return 'bg-yellow-400 text-black hover:bg-yellow-500';
        return 'bg-green-400 text-white hover:bg-green-500';
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Severity vs Occurrence Matrix</CardTitle>
                <CardDescription>Risk distribution by criticality zones (G × O)</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                    <div className="flex items-center gap-4">
                        {/* Y-Axis Label */}
                        <div className="h-full flex flex-col justify-center">
                            <span className="text-[10px] font-bold uppercase vertical-text transform -rotate-180 [writing-mode:vertical-lr] text-muted-foreground tracking-widest">
                                Occurrence (O)
                            </span>
                        </div>

                        <div className="flex-1 w-full max-w-[800px]">
                            {/* Grid Container */}
                            <div className="grid grid-cols-10 gap-[2px] bg-muted/20 border border-muted p-[3px] rounded-md shadow-xl overflow-hidden">
                                {/* Rows (O from 10 down to 1) */}
                                {[...Array(10)].map((_, rIdx) => {
                                    const o = 10 - rIdx;
                                    return (
                                        <div key={o} className="contents">
                                            {[...Array(10)].map((_, cIdx) => {
                                                const g = cIdx + 1;
                                                const cell = cells[o - 1]?.[g - 1];
                                                const count = cell?.modes.length || 0;

                                                return (
                                                    <div
                                                        key={`${o}-${g}`}
                                                        className={`
                                                            aspect-square flex items-center justify-center 
                                                            text-[16px] font-extrabold cursor-help transition-all duration-300
                                                            hover:scale-110 hover:z-20 hover:shadow-2xl
                                                            ${getCellColor(cell)}
                                                        `}
                                                        title={`G:${g}, O:${o} - ${count} failures`}
                                                    >
                                                        {count > 0 ? count : ''}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* X-Axis labels */}
                            <div className="grid grid-cols-10 mt-4">
                                {[...Array(10)].map((_, i) => (
                                    <div key={i} className="text-center text-[13px] font-mono font-black text-muted-foreground">
                                        {i + 1}
                                    </div>
                                ))}
                            </div>
                            <div className="text-center mt-6 text-[12px] font-black uppercase tracking-[0.4em] text-muted-foreground/80">
                                Severity / Gravity (G)
                            </div>
                        </div>
                    </div>
                </div>

                {/* Legend */}
                <div className="mt-6 flex flex-wrap gap-4 text-xs">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-red-500 rounded"></div>
                        <span>Critical (RPN ≥ 200)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-orange-400 rounded"></div>
                        <span>High (RPN ≥ 100)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-yellow-400 rounded"></div>
                        <span>Medium (RPN ≥ 50)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-green-400 rounded"></div>
                        <span>Low (RPN &lt; 50)</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
