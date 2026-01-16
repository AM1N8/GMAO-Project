
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from '@kit/ui/sheet';
import { Button } from '@kit/ui/button';
import { BookOpen, Info } from 'lucide-react';

export function DocumentationSheet() {
    return (
        <Sheet>
            <SheetTrigger asChild>
                <Button variant="outline">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Documentation
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Training Priority Analysis</SheetTitle>
                    <SheetDescription>
                        Methodology and Algorithm Explanation
                    </SheetDescription>
                </SheetHeader>

                <div className="py-6 space-y-6 text-sm">
                    <section className="space-y-2">
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                            <Info className="h-4 w-4 text-primary" />
                            Objective
                        </h3>
                        <p className="text-muted-foreground">
                            This module identifies the most critical technical training needs by correlating
                            theoretical risk (AMDEC/FMEA) with actual field breakdown data.
                            It aims to optimize the training budget by targeting skills that will
                            most effectively reduce machine downtime.
                        </p>
                    </section>

                    <section className="space-y-3">
                        <h3 className="font-semibold text-lg">Calculation Formula</h3>
                        <div className="p-4 bg-muted rounded-md font-mono text-xs overflow-x-auto">
                            TPS = RPN_avg × Freq × Diff × Safety
                        </div>
                        <ul className="space-y-2 list-disc list-inside text-muted-foreground">
                            <li>
                                <strong className="text-foreground">RPN_avg:</strong> Average Risk Priority Number from AMDEC analysis (Severity × Occurrence × Detection).
                            </li>
                            <li>
                                <strong className="text-foreground">Freq (Frequency):</strong> Number of interventions for this failure type in the selected period.
                            </li>
                            <li>
                                <strong className="text-foreground">Diff (Difficulty):</strong> Ratio of failed or delayed interventions to total interventions.
                            </li>
                            <li>
                                <strong className="text-foreground">Safety (Safety Factor):</strong>
                                <ul className="list-inside pl-4 mt-1 space-y-1 text-xs">
                                    <li>1.5x for Electrical (Regulatory/Safety risks)</li>
                                    <li>1.3x for Hydraulic (High pressure/pollution risks)</li>
                                    <li>1.0x for Standard Mechanical</li>
                                </ul>
                            </li>
                        </ul>
                    </section>

                    <section className="space-y-2">
                        <h3 className="font-semibold text-lg">Priority Classification</h3>
                        <div className="grid grid-cols-1 gap-2">
                            <div className="flex items-center gap-2 border p-2 rounded">
                                <div className="h-3 w-3 rounded-full bg-red-500"></div>
                                <span className="font-medium">HIGH (Top 10%)</span>
                                <span className="text-xs text-muted-foreground ml-auto">Urgent Action</span>
                            </div>
                            <div className="flex items-center gap-2 border p-2 rounded">
                                <div className="h-3 w-3 rounded-full bg-amber-500"></div>
                                <span className="font-medium">MEDIUM (Above Avg)</span>
                                <span className="text-xs text-muted-foreground ml-auto">Plan Training</span>
                            </div>
                            <div className="flex items-center gap-2 border p-2 rounded">
                                <div className="h-3 w-3 rounded-full bg-green-500"></div>
                                <span className="font-medium">LOW (Below Avg)</span>
                                <span className="text-xs text-muted-foreground ml-auto">Monitor</span>
                            </div>
                        </div>
                    </section>

                    <section className="space-y-2">
                        <h3 className="font-semibold text-lg">Academic Context</h3>
                        <p className="text-muted-foreground">
                            This deterministic algorithm ensures explainability and reproducibility,
                            unlike "Black Box" AI models. It bridges the gap between static risk analysis
                            and dynamic operational reality.
                        </p>
                    </section>
                </div>
            </SheetContent>
        </Sheet>
    );
}
