"""Bounded broad declaration syntax is independent of ABI qualification."""
import dataclasses
import unittest


class BroadDeclarationTests(unittest.TestCase):
    def parse(self, symbol, **kwargs):
        from airs.swift_declaration_profiles import parse_broad_declaration
        return parse_broad_declaration(symbol, **kwargs)

    def test_free_function_ast(self):
        result = self.parse('$s4Test3fooyS2iKF')
        self.assertTrue(result.supported, result)
        self.assertEqual(result.identity.parameter_types[0].name, 'Swift.Int')
        self.assertEqual(result.identity.result_type.name, 'Swift.Int')
        self.assertTrue(result.identity.throws)
        self.assertFalse(hasattr(result.identity, 'error_register'))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.identity.function_name = 'changed'

    def test_nominal_contexts_and_static(self):
        for code, kind in [('V', 'struct_instance_method'), ('O', 'enum_instance_method'), ('C', 'class_instance_method')]:
            with self.subTest(code=code):
                result = self.parse(f'_$s4Test5OuterV5Inner{code}3fooyS2iKF')
                self.assertTrue(result.supported, result)
                self.assertEqual(result.identity.callable_kind.value, kind)
                self.assertEqual([c.name for c in result.identity.context], ['Outer', 'Inner'])
                static = self.parse(f'$s4Test5Owner{code}3fooyS2iKFZ')
                self.assertEqual(static.identity.callable_kind.value, 'static_method')

    def test_types_parameters_and_labels(self):
        cases = [('$s4Test3fooyyKF', [], 'Swift.Void'),
                 ('$s4Test3fooSiyKF', [], 'Swift.Int'),
                 ('$s4Test3foo1a1bSiSi_SdtKF', ['Swift.Int', 'Swift.Double'], 'Swift.Int'),
                 ('$s4Test3fooyySiSgzKF', ['Optional'], 'Swift.Void'),
                 ('$s4Test3fooyySf_SbtKF', ['Swift.Float', 'Swift.Bool'], 'Swift.Void'),
                 ('$s4Test3fooyys4Int8V_s6UInt64VtKF', ['Swift.Int8', 'Swift.UInt64'], 'Swift.Void')]
        for symbol, parameters, result_name in cases:
            with self.subTest(symbol=symbol):
                result = self.parse(symbol)
                self.assertTrue(result.supported, result)
                self.assertEqual([p.name for p in result.identity.parameter_types], parameters)
                self.assertEqual(result.identity.result_type.name, result_name)
        labeled = self.parse('$s4Test3foo1a1bSiSi_SdtKF').identity
        self.assertEqual(labeled.parameter_labels, ('a', 'b'))
        self.assertTrue(self.parse('$s4Test3fooyySiSgzKF').identity.parameter_types[0].inout)

    def test_generics_and_known_substitutions(self):
        generic = self.parse('$s4Test3fooyxxlF')
        self.assertTrue(generic.supported, generic)
        self.assertEqual(generic.identity.generic_parameter_counts, (1,))
        repeated = self.parse('$s4Test5OwnerV3fooyA2ZKF')
        self.assertFalse(repeated.supported)  # index 25 is absent; never invent a type
        nominal = self.parse('$s4Test5OwnerV3fooyA2CKF')
        self.assertTrue(nominal.supported, nominal)
        self.assertEqual(nominal.identity.result_type.name, 'Test.Owner')

    def test_explicit_family_refusals(self):
        cases = [('$s4Test3fooyyYaKF', 'async_context'),
                 ('$s4Test3fooyyAA5ErrorOYKF', 'typed_throws'),
                 ('$s4Test3fooyyKFTj', 'thunk_or_specialization'),
                 ('$s4Test3fooyyKFTg5', 'thunk_or_specialization'),
                 ('$s4Test3fooyyKFTW', 'thunk_or_specialization'),
                 ('$s4Test3fooyS2iKcKF', 'closure_type'),
                 ('$s4Test3fooyS2iKXEKF', 'closure_type'),
                 ('$s4Test3fooyyKFAA', 'unconsumed_suffix'),
                 ('$s4Test0012vergenza_JFayyF', 'unicode_identifier'),
                 ('$s4Test5OwnerV3fooyxxs13BinaryIntegerRzlF', 'generic_requirements'),
                 ('$s4Test5ActorC3fooyyYaKF', 'async_context'),
                 ('$s4Test5ProtoP3fooyyKF', 'protocol_context')]
        for symbol, reason in cases:
            with self.subTest(symbol=symbol):
                result = self.parse(symbol)
                self.assertFalse(result.supported, result)
                self.assertEqual(result.unsupported_reason.value, reason)
                self.assertIsNone(result.identity)

    def test_bounds_and_malformed_input(self):
        from airs.swift_declaration_profiles import ParseLimits
        for symbol in (None, '', '$s', '$s9999999999999999999999999Test', '$s4Test3fooyAZKF', '$s4Test3fooyyKFjunk', '$s4Test3fooyyKF\x01'):
            self.assertFalse(self.parse(symbol).supported)
        self.assertEqual(self.parse('$s4Test3fooyS2iKF', limits=ParseLimits(max_symbol_length=4)).unsupported_reason.value, 'resource_limit')
        self.assertEqual(self.parse('$s4Test5OwnerV3fooyyKF', limits=ParseLimits(max_substitutions=1)).unsupported_reason.value, 'resource_limit')

    def test_annotation_order_and_full_type_tree(self):
        for symbol in ('$s4Test3fooKyS2iF', '$s4Test3fooyS2iKSiF',
                       '$s4Test3fooyS2illF', '$s4Test3fooyS2iKlKF'):
            self.assertFalse(self.parse(symbol).supported, symbol)
        result = self.parse('$s4Test3fooyySaySiGKF')
        self.assertTrue(result.supported, result)
        self.assertEqual(result.identity.parameter_types[0].name, 'Swift.Array')
        self.assertEqual(result.identity.parameter_types[0].arguments[0].name, 'Swift.Int')
        nested = self.parse('$s4Test3fooyySi_Sd_SbttKF')
        self.assertTrue(nested.supported, nested)
        self.assertEqual(nested.identity.parameter_types[1].name, 'Tuple')
        self.assertEqual([t.name for t in nested.identity.parameter_types[1].arguments], ['Swift.Double', 'Swift.Bool'])

    def test_labels_are_not_types_and_generic_bindings_are_required(self):
        for symbol in ('$s4Test3fooyAAKF', '$s4Test3fooyxxF',
                       '$s4Test3fooyxq_lF', '$s4Test3fooyyKFZ',
                       '$s4Test3foo1a1bS2iKF'):
            self.assertFalse(self.parse(symbol).supported, symbol)

    def test_type_depth_budget_and_mixed_labels(self):
        from airs.swift_declaration_profiles import ParseLimits
        limited = self.parse('$s4Test3fooyySiSgSgKF', limits=ParseLimits(max_type_depth=2))
        self.assertEqual(limited.unsupported_reason.value, 'resource_limit')
        mixed = self.parse('$s4Test3foo_1bSiSi_SdtKF')
        self.assertTrue(mixed.supported, mixed)
        self.assertEqual(mixed.identity.parameter_labels, (None, 'b'))

    def test_recorded_owned_word_substituted_contexts(self):
        # Raw spellings retained by the existing independent LLVM/nm index.
        cases = [
            ('_$s10BroadOwned0A9Owner0099V15broad_case_0099ySis6UInt64V_Sis5Int32VtKF', 'struct_instance_method', 'BroadOwner0099'),
            ('_$s10BroadOwned0A9Owner0180O15broad_case_0180ySis5Int32V_SbSdtKF', 'enum_instance_method', 'BroadOwner0180'),
            ('_$s10BroadOwned0A9Owner0235C15broad_case_0235yS2i_SSSitKF', 'class_instance_method', 'BroadOwner0235'),
        ]
        for symbol, kind, owner in cases:
            result = self.parse(symbol)
            self.assertTrue(result.supported, result)
            self.assertEqual(result.identity.context[0].name, owner)
            self.assertEqual(result.identity.callable_kind.value, kind)
        self.assertEqual(self.parse('$s10BroadOwned0Z9Owner0099V3fooyyF').unsupported_reason.value, 'unknown_substitution')
        for symbol in (
            '_$s10BroadOwned15broad_case_0001yS2i_Sis5Int32VtKF',
            '_$s10BroadOwned0A9Owner0295V15broad_case_0295ySis5Int32V_SaySiGSbtKFZ',
            '_$s10BroadOwned0A9Owner0340V15broad_case_0340yS2i_S2SxtKSzRzlFZ',
            '_$s10BroadOwned0A9Owner0375V15broad_case_0375ySis5Int32V_SdSStKF',
        ):
            result = self.parse(symbol)
            self.assertTrue(result.supported, result)
        typed = self.parse('_$s10BroadOwned0A9Owner0084V15broad_case_0084ySis5Int32V_SSSitAA0A5ErrorOYKF')
        self.assertEqual(typed.unsupported_reason.value, 'typed_throws')


    def test_recorded_generic_requirement_and_specialized_refusal(self):
        base = '_$s10BroadOwned0A9Owner0363V15broad_case_0363ySis5Int32V_s6UInt64VSixtKSzRzlFZ'
        result = self.parse(base)
        self.assertTrue(result.supported, result)
        self.assertEqual(result.identity.generic_requirements[0].protocol, 'Swift.BinaryInteger')
        self.assertEqual(result.identity.generic_requirements[0].parameter_index, 0)
        specialized = self.parse(base + 'Si_Tt3g5')
        self.assertTrue(specialized.supported, specialized)
        self.assertEqual(specialized.identity.specialization.dropped_argument_ordinals, (4,))

    def test_word_reference_terminators_and_literal_word_boundaries(self):
        # Short/numeric fragments never occupy the 26-entry word dictionary.
        for symbol in ('$s10BroadOwned0AV3fooyyF', '$s10BroadOwned0z9Owner0099V3fooyyF'):
            self.assertFalse(self.parse(symbol).supported, symbol)
        exact = self.parse('$s10BroadOwned0A4_009V3fooyyF')
        self.assertTrue(exact.supported, exact)
        self.assertEqual(exact.identity.context[0].name, 'Broad_009')

    def test_review_duplicate_generic_signature_refuses(self):
        for symbol in ('$s4Test3fooyxxlrlF', '$s4Test3fooyxxr_lr_lF'):
            result = self.parse(symbol)
            self.assertFalse(result.supported, symbol)
            self.assertEqual(result.unsupported_reason.value, 'invalid_grammar')

    def test_review_requirement_binding_refuses_zero_count(self):
        result = self.parse('$s4Test3fooyySzRzrzlF')
        self.assertFalse(result.supported, result)
        self.assertEqual(result.unsupported_reason.value, 'generic_requirements')

    def test_review_nominal_context_preserves_type_role(self):
        for symbol in ('$s4Test3fooySi_Sdt3BadVyF',
                       '$s4Test3fooyx3BadVylF',
                       '$s4Test3fooySaySiG3BadVyF'):
            result = self.parse(symbol)
            self.assertFalse(result.supported, symbol)
            self.assertEqual(result.unsupported_reason.value, 'invalid_grammar')
        nominal = self.parse('$s4Test5OwnerV3fooyAC3SubVyF')
        self.assertTrue(nominal.supported, nominal)
        self.assertEqual(nominal.identity.result_type.name, 'Test.Owner.Sub')

    def test_specialization_recorded_concrete_binding_preserves_template(self):
        base = '_$s10BroadOwned0A9Owner0363V15broad_case_0363ySis5Int32V_s6UInt64VSixtKSzRzlFZ'
        result = self.parse(base + 'Si_Tt3g5')
        self.assertTrue(result.supported, result)
        identity = result.identity
        self.assertEqual(identity.callable_kind.value, 'generic_specialization')
        self.assertEqual(identity.original_callable_kind.value, 'static_method')
        self.assertEqual(identity.parameter_types[-1].name, 'GenericParameter')
        spec = identity.specialization
        self.assertEqual(spec.kind.value, 'generic_reabstracted')
        self.assertEqual(spec.pass_id, 5)
        self.assertEqual(spec.dropped_argument_ordinals, (4,))
        self.assertEqual(spec.bindings[0].replacement.name, 'Swift.Int')
        self.assertEqual(spec.substituted_parameter_types[-1].name, 'Swift.Int')
        self.assertEqual(len(spec.substituted_parameter_types), 4)
        self.assertEqual(spec.template_symbol, base)

    def test_specialization_pure_flags_and_nested_source_types(self):
        result = self.parse('$s4Test3fooyxxlFSi_Tgq5')
        self.assertTrue(result.supported, result)
        self.assertTrue(result.identity.specialization.serialized)
        self.assertEqual(result.identity.specialization.dropped_argument_ordinals, ())
        nested = self.parse('$s4Test3fooyxSgxlFSi_TG5')
        self.assertTrue(nested.supported, nested)
        self.assertEqual(nested.identity.specialization.substituted_result_type.arguments[0].name, 'Swift.Int')

    def test_specialization_malformed_and_abi_changing_refusals(self):
        base = '$s4Test3fooyxxlF'
        for suffix in ('Si_Tg', 'Si_Tg55', 'Si_TgX5', 'Si_Tt3g5junk',
                       'Si_Tt3t3g5', 'Si_SdTg5', 'x_Tg5', 'SiTg5', 'Si_SgTg5'):
            result = self.parse(base + suffix)
            self.assertFalse(result.supported, suffix)
            self.assertIsNone(result.identity)
        for suffix in ('Tf4nnnd_n', 'Tf4nnn_n', 'TA', 'Tp5'):
            result = self.parse(base + suffix)
            self.assertFalse(result.supported, suffix)
            self.assertEqual(result.unsupported_reason.value, 'thunk_or_specialization')

    def test_specialization_attributes_and_binding_scope(self):
        result = self.parse('$s4Test3fooyxxlFSi_Ttt1gqar5')
        self.assertTrue(result.supported, result)
        spec = result.identity.specialization
        self.assertEqual((spec.serialized, spec.async_removed, spec.representation_changed), (True, True, True))
        self.assertEqual(spec.dropped_argument_ordinals, (0, 2))
        fixed = self.parse('$s4Test3fooyxxlFs5Int32V_TB5')
        self.assertTrue(fixed.supported, fixed)
        self.assertEqual(fixed.identity.specialization.bindings[0].replacement.name, 'Swift.Int32')
        for symbol in ('$s4Test3fooyyFSi_Tg5', '$s4Test3fooyxxr__lFSi_Tg5'):
            result = self.parse(symbol)
            self.assertFalse(result.supported, symbol)
            self.assertEqual(result.unsupported_reason.value, 'generic_requirements')
