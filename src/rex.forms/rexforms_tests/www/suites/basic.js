module("basic", {
    setup: function () {
        node().append(getPageTemplate('basic'));
        window.rexFormsClient = createRexFormsClient({}, 'basic');
        $(window.rexFormsClient).bind('rexforms:forwardError', function (event, eventRetData) {
        	eventRetData.cancel = true;
        });
    },
    teardown: function () {
		var questions = rexFormsClient.form.questions;
		$.each(questions, function (_, question) {
			question.setValue(null, false);
		});
        rexFormsClient.goToStart();
    }
});

test('created properly', function () {
	equal(rexFormsClient.form.pages.length, 4, "all pages are created");
	equal(objSize(rexFormsClient.form.questions), 10, "all questions are created");
	equal(rexFormsClient.currentPageIdx, 0, "first page is current");
    text('#basic_form_title', 'Test Form');
    text('#basic_page_title', 'First Test Page');
    html('#basic_page_introduction', 'Test <strong>Creole</strong>');
});

test('moving through pages', function () {
	var questions = rexFormsClient.form.questions;

	questions['test_required'].setValue(null, false);
	rexFormsClient.nextPage();
	equal(rexFormsClient.currentPageIdx, 0, "step to next page is blocked due to missed required question");

	questions['test_required'].setValue(1, false);
	rexFormsClient.nextPage();
	equal(rexFormsClient.currentPageIdx, 1, "step to next page succeeds");

	rexFormsClient.prevPage();
	equal(rexFormsClient.currentPageIdx, 0, "step back to previous page succeeds");
});

test('test integer question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_integer'].setValue(5.1, false);
		},
		/InvalidValue/,
		"setting float is not allowed"
	);

	throws(
		function () {
			questions['test_integer'].setValue('abc', false);
		},
		/InvalidValue/,
		"setting non-numeric value is not allowed"
	);

	questions['test_integer'].setValue(5, false);
	equal(questions['test_integer'].getValue(), 5, 'setting and getting value');

	var rexlValue = questions['test_integer'].getRexlValue();
	equal(rexlValue.value, 5, "right rexl value");

	ok(!questions['test_integer'].isIncorrect(), 'is correct');

	var editNode = questions['test_integer'].edit();
	var input = editNode.find('.rf-question-answers input');
	equal(input.size(), 1, 'edit node of integer has input element');

	input.val('1.1');
	input.change();
	ok(questions['test_integer'].isIncorrect(), 'floats are not allowed');

	input.val('a');
	input.change();
	ok(questions['test_integer'].isIncorrect(), 'non-numeric numbers are not allowed');

	input.val('9');
	input.change();
	ok(!questions['test_integer'].isIncorrect(), 'numeric numbers are acceptable');

    equal(questions['test_integer'].getValue(), 9, 'extracting value succeeds');

	questions['test_integer'].setAnnotation('do_not_want');
	equal(questions['test_integer'].getValue(), null, 'Numeric question is cleared after setting annotation');
	equal(questions['test_integer'].annotation, 'do_not_want', 'Annotation for numeric question is set correctly');
});

test('test float question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_float'].setValue('abc', false);
		},
		/InvalidValue/,
		"setting non-numeric value is not allowed"
	);

	questions['test_float'].setValue(5.1, false);
	equal(questions['test_float'].getValue(), 5.1, 'setting and getting value');

	var rexlValue = questions['test_float'].getRexlValue();
	equal(rexlValue.value, 5.1, "right rexl value");

	ok(!questions['test_float'].isIncorrect(), 'is correct');

	var editNode = questions['test_float'].edit();
	var input = editNode.find('.rf-question-answers input');
	equal(input.size(), 1, 'edit node of float has input element');

	input.val('a');
	input.change();
	ok(questions['test_float'].isIncorrect(), 'non-numeric numbers are not allowed');

	input.val('9');
	input.change();
	ok(!questions['test_float'].isIncorrect(), 'intger numbers are acceptable');

	input.val('1.1');
	input.change();
	ok(!questions['test_float'].isIncorrect(), 'floats are acceptable');

    equal(questions['test_float'].getValue(), 1.1, 'extracting value succeeds');
});

test('test string question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_string'].setValue(1, false);
		},
		/InvalidValue/,
		"setting non-string value is not allowed"
	);

	questions['test_string'].setValue('Test string', false);
	equal(questions['test_string'].getValue(), 'Test string', 'setting and getting value');

	var rexlValue = questions['test_string'].getRexlValue();
	equal(rexlValue.value, 'Test string', "right rexl value");

	ok(!questions['test_string'].isIncorrect(), 'is correct');

	var editNode = questions['test_string'].edit();
	var input = editNode.find('.rf-question-answers input').add('.rf-question-answers textarea');
	equal(input.size(), 1, 'edit node of string has input element');

	input.val('  should be trimmed   ');
	input.change();
	ok(!questions['test_string'].isIncorrect(), 'string is acceptable');

    equal(questions['test_string'].getValue(), 'should be trimmed', 'extracting and trimming value succeeds');

	questions['test_string'].setAnnotation('do_not_want');
	equal(questions['test_string'].getValue(), null, 'String question is cleared after setting annotation');
	equal(questions['test_string'].annotation, 'do_not_want', 'Annotation for string question is set correctly');
});

test('test date question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_date'].setValue(1, false);
		},
		/InvalidValue/,
		"setting non-string value is not allowed"
	);

	throws(
		function () {
			questions['test_date'].setValue('2013-13-30', false);
		},
		/InvalidValue/,
		"invalid date is not allowed"
	);

	questions['test_date'].setValue('2013-03-19', false);
	equal(questions['test_date'].getValue(), '2013-03-19', 'setting and getting value');

	var rexlValue = questions['test_date'].getRexlValue();
	equal(rexlValue.value, '2013-03-19', "right rexl value");

	ok(!questions['test_date'].isIncorrect(), 'is correct');

	var editNode = questions['test_date'].edit();
	var input = editNode.find('.rf-question-answers input');
	equal(input.size(), 1, 'edit node of string has input element');

	input.val('  2013-03-20   ');
	input.change();
	ok(!questions['test_date'].isIncorrect(), 'string is acceptable');

    equal(questions['test_date'].getValue(), '2013-03-20', 'extracting and trimming value succeeds');

	questions['test_date'].setAnnotation('do_not_want');
	equal(questions['test_date'].getValue(), null, 'Date question is cleared after setting annotation');
	equal(questions['test_date'].annotation, 'do_not_want', 'Annotation for date question is set correctly');
});

test('test enum question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_enum'].setValue('var4', false);
		},
		/InvalidValue/,
		"enum should accept only valid variant as its value"
	);

	questions['test_enum'].setValue('var1', false);
	equal(questions['test_enum'].getValue(), 'var1', 'setting and getting value');

	var rexlValue = questions['test_enum'].getRexlValue();
	equal(rexlValue.value, 'var1', "right rexl value");
	ok(!questions['test_enum'].isIncorrect(), 'is correct');

	var editNode = questions['test_enum'].edit();
	var input = editNode.find('.rf-question-answers input[type=radio]');
	equal(input.size(), 3, 'edit node of enum has input elements: one for each variant');

	input.removeAttr('checked');
	input.filter('[value=var3]').attr('checked', 'checked').change();
	ok(!questions['test_enum'].isIncorrect(), 'another variant is acceptable');

    equal(questions['test_enum'].getValue(), 'var3', 'extracting value succeeds');

	questions['test_enum'].setAnnotation('do_not_want');
	equal(questions['test_enum'].getValue(), null, 'Enum question is cleared after setting annotation');
	equal(questions['test_enum'].annotation, 'do_not_want', 'Annotation for enum question is set correctly');
});

test('test set question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_set'].setValue({'var4':true}, false);
		},
		/InvalidValue/,
		"set should accept only valid variants"
	);

	questions['test_set'].setValue({'var1':false, 'var2':true, 'var3':true}, false);
	var value = questions['test_set'].getValue();
	ok(!value.var1 && value.var2 && value.var3, 'setting and getting value');

	var rexlValue = questions['test_set'].getRexlValue();
	equal(rexlValue.value, 2, "right common rexl value");

	rexlValue = questions['test_set'].getRexlValue(['var2']);
	equal(rexlValue.value, true, "right attribute rexl value");

	ok(!questions['test_set'].isIncorrect(), 'is correct');

	var editNode = questions['test_set'].edit();
	var input = editNode.find('.rf-question-answers input[type=checkbox]');
	questions['test_set'].setValue(null, false);
	equal(input.size(), 3, 'edit node of set has input elements: one for each variant');

	input.filter('[value=var1]').attr('checked', 'checked');
	input.filter('[value=var3]').attr('checked', 'checked').change();
	ok(!questions['test_string'].isIncorrect(), 'choosing variants is acceptable');

	var value = questions['test_set'].getValue();
	ok(value.var1 && !value.var2 && value.var3, 'extracting value succeeds');

	questions['test_set'].setAnnotation('do_not_want');
	value = questions['test_set'].getValue();
	ok(!value.var1 && !value.var2 && !value.var3, 'Set question is cleared after setting annotation');
	equal(questions['test_set'].annotation, 'do_not_want', 'Annotation for set question is set correctly');
});

test('test dual number question', function () {
	var questions = rexFormsClient.form.questions;

	throws(
		function () {
			questions['test_dual'].setValue('abc', false);
		},
		/InvalidValue/,
		"setting non-numeric value is not allowed"
	);

	questions['test_dual'].setValue(5.1, false);
	equal(questions['test_dual'].getValue(), 5.1, 'setting and getting value');

	var rexlValue = questions['test_dual'].getRexlValue();
	equal(rexlValue.value, 5.1, "right rexl value");

	ok(!questions['test_dual'].isIncorrect(), 'is correct');

	var editNode = questions['test_dual'].edit();
	var input = editNode.find('.rf-question-answers input');
	equal(input.size(), 2, 'edit node has two input elements');

	var first = $(input.get(0));
	var second = $(input.get(1));

	first.val('a');
	second.val('').change();
	ok(questions['test_dual'].isIncorrect(), 'non-numeric numbers are not allowed in the first field');

	first.val('');
	second.val('a').change();
	ok(questions['test_dual'].isIncorrect(), 'non-numeric numbers are not allowed in the second field');

	first.val('9');
	second.val('');
	input.change();
	ok(!questions['test_dual'].isIncorrect(), 'intger numbers are acceptable');

	first.val('31');
	second.val('5').change();
	input.change();
	ok(!questions['test_dual'].isIncorrect(), 'numbers are acceptable');

	var question = questions['test_dual'];
    equal(Math.floor(question.getValue()), 31 * question.domain.size + 5, 'extracting value succeeds');

	question.setAnnotation('do_not_want');
	equal(question.getValue(), null, 'Dual question is cleared after setting annotation');
	equal(question.annotation, 'do_not_want', 'Annotation for dual question is set correctly');
});

test('test repeating group', function () {
	var questions = rexFormsClient.form.questions;
	var initialValue = [
		{
			'first_item': 1,
			'second_item': 2
		},
		{
			'first_item': 3,
			'second_item': 4
		},
		{
			'first_item': 5,
			'second_item': 6
		}
	];
	questions['test_rep_group'].setValue(initialValue, false);
	var value = questions['test_rep_group'].getValue();

	equal(value.length, 3, 'repeating group question has right number of groups');
	var firstGroupOk = (value[0]['first_item'] == 1 && value[0]['second_item'] == 2);
	var secondGroupOk = (value[1]['first_item'] == 3 && value[1]['second_item'] == 4);
	var thirdGroupOk = (value[2]['first_item'] == 5 && value[2]['second_item'] == 6);
	ok(firstGroupOk && secondGroupOk && thirdGroupOk, 'setting and getting value succeeds');

	var rexlValue = questions['test_rep_group'].getRexlValue();
	equal(rexlValue.value, 3, "right common rexl value");

	ok(!questions['test_rep_group'].isIncorrect(), 'is correct');

	questions['test_rep_group'].setAnnotation('do_not_want');
	equal(questions['test_rep_group'].getValue(), null, 'Dual question is cleared after setting annotation');
	equal(questions['test_rep_group'].annotation, 'do_not_want', 'Annotation for dual question is set correctly');

	questions['test_rep_group'].setValue(initialValue, false);
	var editNode = questions['test_rep_group'].edit();
	var records = editNode.find('.rf-record');
	equal(records.size(), 3, 'groups are rendered');

	var removeBtn = $(records[1]).find('.rf-remove-record');
	removeBtn.click();
	value = questions['test_rep_group'].getValue();
	equal(value.length, 2, 'deleting a group succeeds');
	firstGroupOk = (value[0]['first_item'] == 1 && value[0]['second_item'] == 2);
	secondGroupOk = (value[1]['first_item'] == 5 && value[1]['second_item'] == 6);
	ok(firstGroupOk && secondGroupOk, 'the rest groups has right values');
});