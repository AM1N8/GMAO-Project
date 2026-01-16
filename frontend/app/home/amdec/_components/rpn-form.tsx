'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@kit/ui/form';
import { Input } from '@kit/ui/input';
import { Button } from '@kit/ui/button';
import { Textarea } from '@kit/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@kit/ui/select';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Loader2, Calculator } from 'lucide-react';
import { Badge } from '@kit/ui/badge';
import { Card, CardContent } from '@kit/ui/card';
// Fallback Slider since @kit/ui/slider might be missing
function Slider({ value, onValueChange, min, max, step, className }: {
    value: number[];
    onValueChange: (value: number[]) => void;
    min: number;
    max: number;
    step: number;
    className?: string;
}) {
    return (
        <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value[0]}
            onChange={(e) => onValueChange([parseInt(e.target.value)])}
            className={`w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary ${className || ''}`}
        />
    );
}

const formSchema = z.object({
    failure_mode_id: z.string().min(1, 'Failure mode is required'),
    gravity: z.number().min(1).max(10),
    occurrence: z.number().min(1).max(10),
    detection: z.number().min(1).max(10),
    analyst_name: z.string().max(100).optional(),
    comments: z.string().optional(),
    corrective_action: z.string().optional(),
    action_status: z.string(),
    action_due_date: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface RpnFormProps {
    initialValues?: Partial<FormValues>;
    onSubmit: (values: FormValues) => void;
    isLoading?: boolean;
}

export function RpnForm({ initialValues, onSubmit, isLoading }: RpnFormProps) {
    const api = useGmaoApi();
    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            gravity: 1,
            occurrence: 1,
            detection: 1,
            action_status: 'pending',
            analyst_name: '',
            comments: '',
            corrective_action: '',
            action_due_date: '',
            ...initialValues,
        } as FormValues,
    });

    const { data: failureModes, isLoading: isLoadingModes } = useQuery({
        queryKey: ['failure-modes-list'],
        queryFn: () => api.listFailureModes({ limit: 1000 }),
    });

    const g = form.watch('gravity');
    const o = form.watch('occurrence');
    const d = form.watch('detection');
    const rpn = g * o * d;

    let rpnColor = 'bg-green-100 text-green-800';
    let riskLevel = 'Low';
    if (rpn >= 200) { rpnColor = 'bg-red-100 text-red-800'; riskLevel = 'Critical'; }
    else if (rpn >= 100) { rpnColor = 'bg-orange-100 text-orange-800'; riskLevel = 'High'; }
    else if (rpn >= 50) { rpnColor = 'bg-yellow-100 text-yellow-800'; riskLevel = 'Medium'; }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid gap-6 md:grid-cols-2">
                    <FormField
                        control={form.control}
                        name="failure_mode_id"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Failure Mode</FormLabel>
                                <Select
                                    onValueChange={field.onChange}
                                    defaultValue={field.value}
                                    disabled={isLoadingModes}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select failure mode" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {failureModes?.map((fm: any) => (
                                            <SelectItem key={fm.id} value={fm.id.toString()}>
                                                {fm.mode_name} ({fm.equipment?.designation || fm.equipment_id})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <Card className="bg-muted/30 border-dashed">
                        <CardContent className="pt-6 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <Calculator className="h-6 w-6 text-primary" />
                                <div>
                                    <p className="text-sm font-medium">calculated RPN</p>
                                    <p className="text-xs text-muted-foreground">G × O × D</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <span className={`text-3xl font-bold rounded-lg px-3 py-1 ${rpnColor}`}>
                                    {rpn}
                                </span>
                                <p className="text-[10px] font-bold uppercase mt-1">{riskLevel} Risk</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Sliders for G, O, D */}
                <div className="grid gap-8 p-6 bg-muted rounded-xl border">
                    <FormField
                        control={form.control}
                        name="gravity"
                        render={({ field }) => (
                            <FormItem>
                                <div className="flex items-center justify-between mb-2">
                                    <FormLabel className="text-base">Gravity (G) - Severity of failure</FormLabel>
                                    <Badge variant="secondary" className="h-7 w-7 flex items-center justify-center text-lg font-bold">{field.value}</Badge>
                                </div>
                                <FormControl>
                                    <Slider
                                        min={1}
                                        max={10}
                                        step={1}
                                        value={[field.value]}
                                        onValueChange={(vals: number[]) => field.onChange(vals[0])}
                                        className="py-4"
                                    />
                                </FormControl>
                                <div className="flex justify-between text-[10px] text-muted-foreground">
                                    <span>Negligible (1)</span>
                                    <span>Catastrophic (10)</span>
                                </div>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="occurrence"
                        render={({ field }) => (
                            <FormItem>
                                <div className="flex items-center justify-between mb-2">
                                    <FormLabel className="text-base">Occurrence (O) - Frequency of failure</FormLabel>
                                    <Badge variant="secondary" className="h-7 w-7 flex items-center justify-center text-lg font-bold">{field.value}</Badge>
                                </div>
                                <FormControl>
                                    <Slider
                                        min={1}
                                        max={10}
                                        step={1}
                                        value={[field.value]}
                                        onValueChange={(vals: number[]) => field.onChange(vals[0])}
                                        className="py-4"
                                    />
                                </FormControl>
                                <div className="flex justify-between text-[10px] text-muted-foreground">
                                    <span>Remote (1)</span>
                                    <span>Persistent (10)</span>
                                </div>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="detection"
                        render={({ field }) => (
                            <FormItem>
                                <div className="flex items-center justify-between mb-2">
                                    <FormLabel className="text-base">Detection (D) - Difficulty to detect</FormLabel>
                                    <Badge variant="secondary" className="h-7 w-7 flex items-center justify-center text-lg font-bold">{field.value}</Badge>
                                </div>
                                <FormControl>
                                    <Slider
                                        min={1}
                                        max={10}
                                        step={1}
                                        value={[field.value]}
                                        onValueChange={(vals: number[]) => field.onChange(vals[0])}
                                        className="py-4"
                                    />
                                </FormControl>
                                <div className="flex justify-between text-[10px] text-muted-foreground">
                                    <span>Obvious (1)</span>
                                    <span>Impossible (10)</span>
                                </div>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                    <FormField
                        control={form.control}
                        name="analyst_name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Analyst Name</FormLabel>
                                <FormControl>
                                    <Input placeholder="Who performed this analysis?" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="action_status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Action Status</FormLabel>
                                <Select
                                    onValueChange={field.onChange}
                                    defaultValue={field.value}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="pending">Pending</SelectItem>
                                        <SelectItem value="in_progress">In Progress</SelectItem>
                                        <SelectItem value="completed">Completed</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="corrective_action"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Corrective Action</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="What actions should be taken to reduce RPN?"
                                    className="min-h-[80px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="comments"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Comments</FormLabel>
                            <FormControl>
                                <Textarea placeholder="Additional notes..." {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => window.history.back()}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={isLoading}>
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            'Save RPN Analysis'
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}
