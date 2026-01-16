import { useMemo } from 'react';
import { useSupabase } from '@kit/supabase/hooks/use-supabase';
import { GmaoApiClient } from '../gmao-api';

export function useGmaoApi() {
    const supabase = useSupabase();

    const api = useMemo(() => {
        return new GmaoApiClient(supabase);
    }, [supabase]);

    return api;
}
